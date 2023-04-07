import re
import copy
import json
import random
import logging
from pprint import pformat
from urllib.parse import urlsplit, parse_qsl

import requests
import titanembeds.constants as constants
from config import config
from flask_socketio import emit
from itsdangerous.exc import BadSignature
from quart import Blueprint, abort
from quart import current_app as app
from quart import jsonify, request, session, url_for
from sqlalchemy import and_
from titanembeds import bot_http_client, redis_cache
from titanembeds.cache_keys import (
    channel_ratelimit_key,
    get_client_ipaddr,
    guild_ratelimit_key,
)
from titanembeds.database import (
    AuthenticatedUsers,
    DiscordBotsOrgTransactions,
    Guilds,
    UnauthenticatedBans,
    UnauthenticatedUsers,
    db,
    get_badges,
    query_unauthenticated_users_like,
)
from titanembeds.decorators import (
    abort_if_guild_disabled,
    discord_users_only,
    valid_session_required,
)
from titanembeds.discord_rest import discord_api
from titanembeds.rate_limiter import rate_limiter
from titanembeds.utils import (
    check_guild_existance,
    check_user_in_guild,
    checkUserBanned,
    generate_avatar_url,
    get_forced_role,
    get_guild_channels,
    get_member_roles,
    guild_accepts_visitors,
    guild_query_unauth_users_bool,
    guild_unauthcaptcha_enabled,
    guild_webhooks_enabled,
    int_or_none,
    serializer,
    update_user_status,
    user_unauthenticated,
)

CLEVERBOT_URL = "http://www.cleverbot.com/getreply"
CAPTCHA_URL = "https://www.google.com/recaptcha/api/siteverify"

log = logging.getLogger(__name__)
api = Blueprint("api", __name__)


@api.after_request
async def after_request(response):
    if response.is_json:
        data = await response.get_json()

        try:
            data["session"] = serializer.dumps(copy.deepcopy(dict(session)))
        except TypeError:  # /user/<guild_id> returns a list
            pass

        response.set_data(json.dumps(data))

    return response


@api.before_request
async def before_request():
    if not (authorization := request.headers.get("authorization", None)):
        return

    try:
        data = serializer.loads(authorization)
        session.update(data)
    except BadSignature:
        log.error(f"Bad signature in auth header value")
    except json.JSONDecodeError:
        log.error(f"Could not JSON decode auth header value")


def parse_emoji(text_to_parse, guild_id):
    for emoj in get_guild_emojis(guild_id):
        animated = "a" if emoj.get("animated") else ""
        text_to_parse = text_to_parse.replace(
            f":{emoj['name']}:", f"<{animated}:{emoj['name']}:{emoj['id']}>"
        )
    return text_to_parse


def format_post_content(guild_id, message, db_user):
    illegal_post = False
    illegal_reasons = []
    message = message.replace("<", "\<")
    message = message.replace(">", "\>")
    message = parse_emoji(message, guild_id)

    db_guild = (
        db.session.query(Guilds).filter(Guilds.guild_id == guild_id).first()
    )

    max_len = get_post_content_max_len(guild_id)
    if len(message) > max_len:
        illegal_post = True
        illegal_reasons.append(
            f"Exceeded the following message length: {max_len} characters"
        )

    links = re.findall(
        "http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
        message,
    )
    if not db_guild.chat_links and len(links) > 0:
        illegal_post = True
        illegal_reasons.append("Links is not allowed.")
    elif db_guild.chat_links and not db_guild.bracket_links:
        for link in links:
            message = message.replace(link, f"<{link}>")

    mention_pattern = re.compile(r"\[@[0-9]+\]")
    all_mentions = re.findall(mention_pattern, message)
    if (
        db_guild.mentions_limit != -1
        and len(all_mentions) > db_guild.mentions_limit
    ):
        illegal_post = True
        illegal_reasons.append(
            "Mentions is capped at the following limit: "
            + str(db_guild.mentions_limit)
        )

    for match in all_mentions:
        mention = "<@" + match[2 : len(match) - 1] + ">"
        message = message.replace(match, mention, 1)

    if db_guild.banned_words_enabled:
        banned_words = set(json.loads(db_guild.banned_words))
        if db_guild.banned_words_global_included:
            banned_words = banned_words.union(
                set(constants.GLOBAL_BANNED_WORDS)
            )

        for word in banned_words:
            regex = re.compile(rf"\b{word}\b", re.IGNORECASE)
            if regex.search(message):
                illegal_post = True
                illegal_reasons.append(
                    "The following word is prohibited: " + word
                )

    if not guild_webhooks_enabled(guild_id):
        if session["unauthenticated"]:
            message = (
                f"**[{session['username']}#{session['user_id']}]** {message}"
            )
        else:
            username = session["username"]
            if db_user and db_user["nick"]:
                username = db_user["nick"]

            # I would like to do a @ mention, but i am worried about notify spam
            message = f"**<{username}#{session['discriminator']}>** {message}"

    return message, illegal_post, illegal_reasons


def format_everyone_mention(channel, content):
    if not channel["mention_everyone"]:
        if "@everyone" in content:
            content = content.replace("@everyone", "@\u200Beveryone")
        if "@here" in content:
            content = content.replace("@here", "@\u200Bhere")

    return content


def filter_guild_channel(guild_id, channel_id, force_everyone=False):
    for chan in get_guild_channels(
        guild_id, force_everyone, get_forced_role(guild_id)
    ):
        if chan["channel"]["id"] == channel_id:
            return chan

    return None


async def get_online_discord_users(guild_id, embed):
    apimembers_filtered = {
        int(m["id"]): m for m in await bot_http_client.list_guild_members(guild_id)
    }

    for member in embed["members"]:
        member["hoist-role"] = None
        member["color"] = None
        if apimem := apimembers_filtered.get(int(member["id"])):
            member["hoist-role"] = apimem["hoist-role"]
            member["color"] = apimem["color"]
            member["avatar"] = apimem["avatar"]
            member["avatar_url"] = apimem["avatar_url"]

    return embed["members"]


async def get_online_embed_users(guild_id):
    usrs = await redis_cache.get_online_embed_user_keys(guild_id)

    unauths = (
        db.session.query(UnauthenticatedUsers)
        .filter(
            UnauthenticatedUsers.user_key.in_(usrs["UnauthenticatedUsers"]),
            UnauthenticatedUsers.revoked == False,
            UnauthenticatedUsers.guild_id == guild_id,
        )
        .all()
        if usrs["UnauthenticatedUsers"]
        else []
    )
    users = {
        "unauthenticated": [
            {
                "username": user.username,
                "discriminator": user.discriminator,
            }
            for user in unauths
        ],
        "authenticated": [],
    }

    auths = (
        db.session.query(AuthenticatedUsers)
        .filter(
            AuthenticatedUsers.client_id.in_(usrs["AuthenticatedUsers"]),
            AuthenticatedUsers.guild_id == guild_id,
        )
        .all()
        if usrs["AuthenticatedUsers"]
        else []
    )
    for user in auths:
        usrdb = bot_http_client.get_guild_member(guild_id, user.client_id)
        meta = {
            "id": str(usrdb["id"]),
            "username": usrdb["username"],
            "nickname": usrdb["nick"],
            "discriminator": usrdb["discriminator"],
            "avatar_url": generate_avatar_url(usrdb["id"], usrdb["avatar"]),
        }
        users["authenticated"].append(meta)

    return users


def get_guild_emojis(guild_id):
    return bot_http_client.get_guild(guild_id)["emojis"]


def get_guild_roles(guild_id):
    return bot_http_client.get_guild(guild_id)["roles"]


# Returns webhook url if exists and can post w/webhooks, otherwise None
async def get_channel_webhook(guild_id, channel_id):
    if not guild_webhooks_enabled(guild_id):
        return None

    discrim = (
        session["user_id"]
        if user_unauthenticated()
        else session["discriminator"]
    )
    name = f"[Titan] {session['username'][:19]}#{discrim}"

    webhooks = bot_http_client.get_guild(guild_id)["webhooks"]
    log.info("checking webhook for channel %s and name '%s'", channel_id, name)
    for webhook in webhooks:
        log.info(
            "checking webhook: id: %s, channel_id: %s, name: %s",
            webhook["id"],
            webhook["channel_id"],
            webhook["name"],
        )
    for webhook in webhooks:
        if channel_id == webhook["channel_id"] and webhook["name"] == name:
            log.info("Found guild webhook : %s", webhook)
            return {
                "id": webhook["id"],
                "token": webhook["token"],
                "name": webhook.get("name"),
                "guild_id": webhook.get("guild_id"),
                "channel_id": webhook.get("channel_id"),
            }

    webhook = await discord_api.create_webhook(guild_id, channel_id, name)
    log.info("Created guild webhook : %s", webhook)
    # "Maximum number of webhooks reached (10)"
    if webhook["code"] == 30007 or not webhook:
        return None

    return webhook.get("content") if webhook else None


async def send_webhook(content, db_user, file, guild_id, rich_embed, webhook):
    if session["unauthenticated"]:
        username = f"{session['username'][:25]}#{session['user_id']}"

        if (
            db_guild := db.session.query(Guilds)
            .filter(Guilds.guild_id == guild_id)
            .first()
        ) and db_guild.guest_icon:
            avatar = db_guild.guest_icon
        else:
            avatar = url_for(
                "static",
                filename="img/titanembeds_square.png",
                _external=True,
                _scheme="https",
            )
    else:
        username = (
            db_user["nick"]
            if db_user and db_user["nick"]
            else session["username"]
        )
        username = f"{username[:25]}#{session['discriminator']}"
        avatar = session["avatar"]

    message = discord_api.execute_webhook(
        webhook.get("id"),
        webhook.get("token"),
        username,
        avatar,
        content,
        file,
        rich_embed,
    )
    if message.get("message", {}).get("code") == 10015:  # Unknown webhook
        log.error("Unknown webhook: %s", message)
        return None

    await delete_webhook_if_too_much(guild_id)
    return message


async def delete_webhook_if_too_much(guild_id):
    if not guild_webhooks_enabled(guild_id):
        return

    guild = bot_http_client.get_guild(guild_id)
    titan_webhooks = [
        w for w in guild["webhooks"] if w["name"].startswith("[Titan] ")
    ]

    if len(titan_webhooks) > 0 and len(guild["webhooks"]) >= 8:
        log.info(
            "Webhook count: %s. guild webhooks: %s.",
            len(titan_webhooks),
            len(guild["webhooks"]),
        )
        for wh in titan_webhooks:
            log.info("Deleting excess webhook %s", wh)
            try:
                res = await discord_api.delete_webhook(
                    wh["id"], wh["token"], guild_id
                )
                log.info("delete_webhook result:  %s", pformat(res))
            except:
                log.exception("Could not delete webhook")
                pass  # not my problem now


async def get_all_users(guild_id):
    mem = []
    for u in await bot_http_client.list_guild_members(guild_id):
        mem.append(
            {
                "id": str(u["id"]),
                "avatar": u["avatar"],
                "avatar_url": generate_avatar_url(
                    u["id"], u["avatar"], u["discriminator"], True
                ),
                "username": u["username"],
                "nickname": u["nick"],
                "discriminator": u["discriminator"],
            }
        )

    return mem


@api.route("/fetch", methods=["GET"])
@valid_session_required(api=True)
@abort_if_guild_disabled()
@rate_limiter.limit("2 per 2 second", key_func=channel_ratelimit_key)
# GET
# 	https://ddr-titan.fly.dev/api/fetch?guild_id=1022123131948769430&channel_id=1022123131948769436&after=
async def fetch():
    log.info("fetch")
    guild_id = request.args.get("guild_id")
    channel_id = request.args.get("channel_id")
    after_snowflake = request.args.get("after", 0, type=int)
    key = session["user_keys"][guild_id] if user_unauthenticated() else None
    status = await update_user_status(guild_id, session["username"], key)

    messages = {}

    if status["banned"] or status["revoked"]:
        status_code = 403
        if user_unauthenticated():
            session["user_keys"].pop(guild_id, None)
            session.modified = True
    else:
        if not (chan := filter_guild_channel(guild_id, channel_id)):
            abort(404)

        if not chan.get("read") or chan["channel"]["type"] != "text":
            status_code = 401
        else:
            messages = await bot_http_client.get_channel_messages(
                guild_id, channel_id, after_snowflake
            )
            status_code = 200

    response = jsonify(messages=messages, status=status)
    response.status_code = status_code

    return response


@api.route("/fetch_visitor", methods=["GET"])
@abort_if_guild_disabled()
@rate_limiter.limit("2 per 2 second", key_func=channel_ratelimit_key)
async def fetch_visitor():
    guild_id = request.args.get("guild_id")
    channel_id = request.args.get("channel_id")
    after_snowflake = request.args.get("after", 0, type=int)

    if not guild_accepts_visitors(guild_id):
        abort(403)
    if not (chan := filter_guild_channel(guild_id, channel_id, True)):
        abort(404)

    if not chan.get("read") or chan["channel"]["type"] != "text":
        messages = {}
        status_code = 401
    else:
        messages = await bot_http_client.get_channel_messages(
            guild_id, channel_id, after_snowflake
        )
        status_code = 200

    response = jsonify(messages=messages)
    response.status_code = status_code

    return response


async def get_guild_specific_post_limit():
    form = await request.form
    guild_id = int_or_none(form.get("guild_id", None))

    if guild_id and (
        db_guild := db.session.query(Guilds)
        .filter(Guilds.guild_id == guild_id)
        .first()
    ):
        seconds = db_guild.post_timeout
    else:
        seconds = 5

    return f"1 per {seconds} second"


def get_post_content_max_len(guild_id):
    guild_id = int_or_none(guild_id)

    if guild_id and (
        db_guild := db.session.query(Guilds)
        .filter(Guilds.guild_id == guild_id)
        .first()
    ):
        return db_guild.max_message_length

    return 350


@api.route("/post", methods=["POST"])
@valid_session_required(api=True)
@abort_if_guild_disabled()
# todo  get_guild_specific_post_limit is now async
# @rate_limiter.limit(
#    get_guild_specific_post_limit,
#    key_func=channel_ratelimit_key,
# )
async def post():
    form = await request.form
    guild_id = form.get("guild_id")
    channel_id = form.get("channel_id")
    content = form.get("content", "")

    files = await request.files
    file = getattr(files.get("file"), "filename", None) or None

    rich_embed = json.loads(form.get("richembed", "{}"))

    db_user = (
        bot_http_client.get_guild_member(guild_id, session["user_id"])
        if "user_id" in session
        else None
    )
    key = session["user_keys"][guild_id] if user_unauthenticated() else None

    log.info("post: message is %s", pformat(content))
    content, illegal_post, illegal_reasons = format_post_content(
        guild_id, content, db_user
    )
    chan = filter_guild_channel(guild_id, channel_id)
    content = format_everyone_mention(chan, content)
    log.info("post: message is now %s", pformat(content))

    status = await update_user_status(guild_id, session["username"], key)

    if not content:
        return return_response(204, {}, status)
    if status["banned"] or status["revoked"]:
        return return_response(401, {}, status, illegal_reasons)
    elif not chan.get("write") or chan["channel"]["type"] != "text":
        return return_response(401, {}, status, illegal_reasons)
    elif (file and not chan.get("attach_files")) or (
        rich_embed and not chan.get("embed_links")
    ):
        return return_response(406, {}, status, illegal_reasons)
    elif illegal_post:
        return return_response(417, {}, status, illegal_reasons)

    # if userid in get_administrators_list():
    #     content = "(Titan Dev) " + content
    webhook = await get_channel_webhook(guild_id, channel_id)
    if webhook:
        log.info("sending message by webhook '%s'", webhook)
        # https://discord.com/api/webhooks/1051803851684073502/-bMS3xabIBd7Bz6qdJ3psGVDSHJYqRvtSPp1dMntR1iiHFNYx5EDh9r2WaseDsdxeoLu
        # https://discord.com/api/webhooks/1051804042302599198/E3bq8_tm1eKV1B_STL5IykczUkVHAb5RtvZ53TarQRj-3thsc9Bk7mV9lTGxeGCzkce6
        message = await send_webhook(
            content, db_user, file, guild_id, rich_embed, webhook
        )
        if not message:
            webhook = None

    if not webhook:
        log.info("sending message by discord api")
        message = discord_api.create_message(
            channel_id, content, file, rich_embed
        )

    return return_response(message["code"], message, status, illegal_reasons)


def return_response(status_code, message, status, illegal_reasons=None):
    db.session.commit()
    response = jsonify(
        message=message.get("content", message),
        status=status,
        illegal_reasons=illegal_reasons or [],
    )
    response.status_code = status_code
    return response


def verify_captcha_request(captcha_response, ip_address):
    payload = {
        "secret": config["recaptcha-secret-key"],
        "response": captcha_response,
    }
    if not app.config["DEBUG"]:
        payload["remoteip"] = ip_address

    r = requests.post(CAPTCHA_URL, data=payload).json()

    return r["success"]


@api.route("/create_unauthenticated_user", methods=["POST"])
@rate_limiter.limit("6 per 30 minute", key_func=guild_ratelimit_key)
@abort_if_guild_disabled()
async def create_unauthenticated_user():
    form = await request.form
    session["unauthenticated"] = True
    username = form["username"].strip()
    guild_id = form["guild_id"]
    ip_address = get_client_ipaddr()

    if len(username) < 2 or len(username) > 32:
        abort(406)
    if not all(
        x.isalnum() or x.isspace() or "-" == x or "_" == x for x in username
    ):
        abort(406)
    if not check_guild_existance(guild_id):
        abort(404)
    if not guild_query_unauth_users_bool(guild_id):
        abort(401)

    if guild_unauthcaptcha_enabled(guild_id):
        if not verify_captcha_request(
            form["captcha_response"], request.remote_addr
        ):
            abort(412)

    if not checkUserBanned(guild_id, ip_address):
        session["username"] = username
        if "user_id" not in session or len(str(session["user_id"])) > 4:
            session["user_id"] = random.randint(0, 9999)

        user = UnauthenticatedUsers(
            guild_id, username, session["user_id"], ip_address
        )
        db.session.add(user)

        key = user.user_key
        if "user_keys" not in session:
            session["user_keys"] = {guild_id: key}
        else:
            session["user_keys"][guild_id] = key

        session.permanent = False

        status = await update_user_status(guild_id, username, key)
        final_response = jsonify(status=status)
    else:
        status = {"banned": True}
        final_response = jsonify(status=status)
        final_response.status_code = 403

    db.session.commit()
    return final_response


@api.route("/change_unauthenticated_username", methods=["POST"])
@rate_limiter.limit("1 per 10 minute", key_func=guild_ratelimit_key)
@abort_if_guild_disabled()
async def change_unauthenticated_username():
    form = await request.form
    username = form["username"].strip()
    guild_id = form["guild_id"]
    ip_address = get_client_ipaddr()

    if len(username) < 2 or len(username) > 32:
        abort(406)
    if not all(
        x.isalnum() or x.isspace() or "-" == x or "_" == x for x in username
    ):
        abort(406)
    if not check_guild_existance(guild_id):
        abort(404)
    if not guild_query_unauth_users_bool(guild_id):
        abort(401)

    if not checkUserBanned(guild_id, ip_address):
        if (
            "user_keys" not in session
            or guild_id not in session["user_keys"]
            or not session["unauthenticated"]
        ):
            abort(424)

        emitmsg = {
            "unauthenticated": True,
            "username": session["username"],
            "discriminator": session["user_id"],
        }
        session["username"] = username
        if "user_id" not in session or len(str(session["user_id"])) > 4:
            session["user_id"] = random.randint(0, 9999)

        user = UnauthenticatedUsers(
            guild_id, username, session["user_id"], ip_address
        )
        db.session.add(user)
        key = user.user_key
        session["user_keys"][guild_id] = key
        status = await update_user_status(guild_id, username, key)

        emit(
            "embed_user_disconnect",
            emitmsg,
            room="GUILD_" + guild_id,
            namespace="/gateway",
        )
        final_response = jsonify(status=status)
    else:
        status = {"banned": True}
        response = jsonify(status=status)
        response.status_code = 403
        final_response = response

    db.session.commit()
    return final_response


def get_guild_guest_icon(guild_id):
    guest_icon = (
        db.session.query(Guilds)
        .filter(Guilds.guild_id == guild_id)
        .first()
        .guest_icon
    )
    return (
        guest_icon
        if guest_icon
        else url_for("static", filename="img/titanembeds_square.png")
    )


def process_query_guild(guild_id, visitor=False):
    channels = get_guild_channels(
        guild_id, visitor, forced_role=(get_forced_role(guild_id))
    )

    # Discord members & embed members listed here is moved to its own api endpoint
    if visitor:
        for channel in channels:
            channel["write"] = False

    return jsonify(
        channels=channels,
        discordmembers=([]),
        embedmembers={"authenticated": [], "unauthenticated": []},
        emojis=get_guild_emojis(guild_id),
        roles=get_guild_roles(guild_id),
        guest_icon=get_guild_guest_icon(guild_id),
        instant_invite=None,
    )


@api.route("/query_guild", methods=["GET"])
@valid_session_required(api=True)
@abort_if_guild_disabled()
async def query_guild():
    guild_id = request.args.get("guild_id")

    if not check_guild_existance(guild_id):
        log.warning("could not find guild %s in redis", guild_id)
        abort(404)
    if not check_user_in_guild(guild_id):
        log.warning("user not in guild")
        abort(403)

    return process_query_guild(guild_id)


@api.route("/query_guild_visitor", methods=["GET"])
@abort_if_guild_disabled()
async def query_guild_visitor():
    guild_id = request.args.get("guild_id")

    if not check_guild_existance(guild_id):
        abort(404)
    if not guild_accepts_visitors(guild_id):
        abort(403)

    return process_query_guild(guild_id, True)


@api.route("/server_members", methods=["GET"])
@abort_if_guild_disabled()
@valid_session_required(api=True)
async def server_members():
    guild_id = request.args.get("guild_id", None)

    if not check_guild_existance(guild_id):
        abort(404)
    if not check_user_in_guild(guild_id):
        abort(403)

    return jsonify(await query_server_members(guild_id))


@api.route("/server_members_visitor", methods=["GET"])
@abort_if_guild_disabled()
async def server_members_visitor():
    abort(404)
    guild_id = request.args.get("guild_id", None)

    if not check_guild_existance(guild_id):
        abort(404)
    if not guild_accepts_visitors(guild_id):
        abort(403)

    return jsonify(await query_server_members(guild_id))


async def query_server_members(guild_id):
    widget = discord_api.get_widget(guild_id)
    if widget.get("success", True):
        discordmembers = await get_online_discord_users(guild_id, widget)
        widgetenabled = True
    else:
        discordmembers = [
            {
                "id": 0,
                "color": "FFD6D6",
                "status": "dnd",
                "username": "Discord Server Widget is Currently Disabled",
            }
        ]
        widgetenabled = False

    return {
        "discordmembers": discordmembers,
        "embedmembers": await get_online_embed_users(guild_id),
        "widgetenabled": widgetenabled,
    }


@api.route("/create_authenticated_user", methods=["POST"])
@discord_users_only(api=True)
@abort_if_guild_disabled()
async def create_authenticated_user():
    if session["unauthenticated"]:
        response = jsonify(error=True)
        response.status_code = 401
        return response

    form = await request.form
    guild_id = form.get("guild_id")
    if not check_guild_existance(guild_id):
        abort(404)

    if not check_user_in_guild(guild_id):
        add_member = discord_api.add_guild_member(
            guild_id, session["user_id"], session["user_keys"]["access_token"]
        )
        if not add_member["success"]:
            discord_status_code = add_member["content"].get("code", 0)
            if discord_status_code == 40007:  # user banned from server
                response = jsonify(status={"banned": True})
                response.status_code = 403
            else:
                response = jsonify(add_member)
                response.status_code = 422

            return response

    db_user = (
        db.session.query(AuthenticatedUsers)
        .filter(
            and_(
                AuthenticatedUsers.guild_id == guild_id,
                AuthenticatedUsers.client_id == session["user_id"],
            )
        )
        .first()
    )
    if not db_user:
        db_user = AuthenticatedUsers(guild_id, session["user_id"])
        db.session.add(db_user)
        db.session.commit()

    status = await update_user_status(guild_id, session["username"])
    return jsonify(status=status)


@api.route("/user/<guild_id>/<user_id>")
@abort_if_guild_disabled()
async def user_info(guild_id, user_id):
    usr = {
        "id": None,
        "username": None,
        "nickname": None,
        "discriminator": None,
        "avatar": None,
        "avatar_url": None,
        "roles": [],
        "badges": [],
    }

    member = bot_http_client.get_guild_member(guild_id, user_id)
    if member:
        usr["id"] = str(member["id"])
        usr["username"] = member["username"]
        usr["nickname"] = member["nick"]
        usr["discriminator"] = member["discriminator"]
        usr["avatar"] = member["avatar"]
        usr["avatar_url"] = generate_avatar_url(
            usr["id"], usr["avatar"], usr["discriminator"], True
        )

        roles = get_member_roles(guild_id, user_id)
        guild_roles = bot_http_client.get_guild(guild_id)["roles"]
        usr["roles"] = [
            gr for gr in guild_roles for r in roles if gr["id"] == r
        ]

        usr["badges"] = get_badges(user_id)
        if redis_cache.redis_store.get(f"DiscordBotsOrgVoted/{member['id']}"):
            usr["badges"].append("discordbotsorgvoted")

    return jsonify(usr)


@api.route("/user/<guild_id>")
@abort_if_guild_disabled()
@valid_session_required(api=True)
async def list_users(guild_id):
    return jsonify(await get_all_users(guild_id))


@api.route("/webhook/discordbotsorg/vote", methods=["POST"])
async def webhook_discordbotsorg_vote():
    incoming = await request.get_json()

    if str(config["client-id"]) != str(incoming.get("bot")):
        abort(401)
    if str(request.headers.get("Authorization", "")) != str(
        config.get("discordbotsorg-webhook-secret", "")
    ):
        abort(403)

    user_id = incoming.get("user")
    params = dict(parse_qsl(urlsplit(incoming.get("query", "")).query))

    vote_type = str(incoming.get("type"))
    if vote_type == "upvote":
        redis_cache.redis_store.set(
            f"DiscordBotsOrgVoted/{user_id}", "voted", 86400
        )

    dbl_trans = DiscordBotsOrgTransactions(
        int(user_id), vote_type, int_or_none(params.get("referrer"))
    )
    db.session.add(dbl_trans)
    db.session.commit()

    return "", 204


@api.route("/bot/ban", methods=["POST"])
async def bot_ban():
    if request.headers.get("Authorization", "") != config.get("app-secret", ""):
        return jsonify(error="Authorization header does not match."), 403

    incoming = request.get_json()
    guild_id = incoming.get("guild_id", None)
    placer_id = incoming.get("placer_id", None)
    username = incoming.get("username", None)
    discriminator = incoming.get("discriminator", None)

    if not guild_id or not placer_id or not username:
        return jsonify(error="Missing required parameters."), 400

    db_user = query_unauthenticated_users_like(
        username, guild_id, discriminator
    )
    if not db_user:
        return jsonify(error="Guest user cannot be found."), 404

    db_ban = (
        db.session.query(UnauthenticatedBans)
        .filter(UnauthenticatedBans.guild_id == str(guild_id))
        .filter(UnauthenticatedBans.last_username == db_user.username)
        .filter(UnauthenticatedBans.last_discriminator == db_user.discriminator)
        .first()
    )
    if db_ban is not None:
        if db_ban.lifter_id is None:
            return (
                jsonify(
                    error=f"Guest user, **{db_ban.last_username}#{db_ban.last_discriminator}**, has already been banned."
                ),
                409,
            )
        db.session.delete(db_ban)

    db_ban = UnauthenticatedBans(
        str(guild_id),
        db_user.ip_address,
        db_user.username,
        db_user.discriminator,
        "",
        int(placer_id),
    )
    db.session.add(db_ban)
    db.session.commit()

    return jsonify(
        success=f"Guest user, **{db_ban.last_username}#{db_ban.last_discriminator}**, has successfully been added to the ban list!"
    )


@api.route("/bot/unban", methods=["POST"])
async def bot_unban():
    if request.headers.get("Authorization", "") != config.get("app-secret", ""):
        return jsonify(error="Authorization header does not match."), 403

    incoming = request.get_json()
    guild_id = incoming.get("guild_id", None)
    lifter_id = incoming.get("lifter_id", None)
    username = incoming.get("username", None)
    discriminator = incoming.get("discriminator", None)

    if not guild_id or not lifter_id or not username:
        return jsonify(error="Missing required parameters."), 400

    db_user = query_unauthenticated_users_like(
        username, guild_id, discriminator
    )
    if not db_user:
        return jsonify(error="Guest user cannot be found."), 404

    db_ban = (
        db.session.query(UnauthenticatedBans)
        .filter(UnauthenticatedBans.guild_id == str(guild_id))
        .filter(UnauthenticatedBans.ip_address == db_user.ip_address)
        .first()
    )
    if db_ban is None:
        return (
            jsonify(
                error=f"Guest user **{db_user.username}#{db_user.discriminator}** has not been banned."
            ),
            404,
        )

    if db_ban.lifter_id is not None:
        return (
            jsonify(
                error=f"Guest user **{db_user.username}#{db_user.discriminator}** ban has already been removed."
            ),
            409,
        )

    db_ban.lift_ban(int(lifter_id))
    db.session.commit()

    return jsonify(
        success=f"Guest user, **{db_user.username}#{db_user.discriminator}**, has successfully been removed from the ban list!"
    )


@api.route("/bot/revoke", methods=["POST"])
async def bot_revoke():
    if request.headers.get("Authorization", "") != config.get("app-secret", ""):
        return jsonify(error="Authorization header does not match."), 403
    incoming = request.get_json()
    guild_id = incoming.get("guild_id", None)
    username = incoming.get("username", None)
    discriminator = incoming.get("discriminator", None)

    if not guild_id or not username:
        return jsonify(error="Missing required parameters."), 400

    dbuser = query_unauthenticated_users_like(username, guild_id, discriminator)
    if not dbuser:
        return jsonify(error="Guest user cannot be found."), 404
    elif dbuser.revoked:
        return (
            jsonify(
                error=f"Guest user **{dbuser.username}#{dbuser.discriminator}** has already been kicked!"
            ),
            409,
        )

    dbuser.revoked = True
    db.session.commit()
    return jsonify(
        success=f"Successfully kicked **{dbuser.username}#{dbuser.discriminator}**!"
    )


@api.route("/bot/members")
async def bot_members():
    if request.headers.get("Authorization", "") != config.get("app-secret", ""):
        return jsonify(error="Authorization header does not match."), 403

    return jsonify(await get_online_embed_users(request.args.get("guild_id")))


@api.route("/af/direct_message", methods=["POST"])
async def af_direct_message_post():
    form = await request.form
    payload = {
        "key": config["cleverbot-api-key"],
        "cs": form.get("cs", None),
        "input": form.get("input"),
    }
    r = requests.get(CLEVERBOT_URL, params=payload)

    return jsonify(r.json())
