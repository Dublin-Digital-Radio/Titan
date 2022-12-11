import re
import copy
import json
import random
import logging
from urllib.parse import urlsplit, parse_qsl

import requests
import titanembeds.constants as constants
from config import config
from flask import Blueprint, abort
from flask import current_app as app
from flask import jsonify, request, session, url_for
from flask_socketio import emit
from itsdangerous.exc import BadSignature
from sqlalchemy import and_
from titanembeds import rate_limiter, redisqueue
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

log = logging.getLogger(__name__)
api = Blueprint("api", __name__)


@api.after_request
def after_request(response):
    if response.is_json:
        data = response.get_json()

        try:
            data["session"] = serializer.dumps(copy.deepcopy(dict(session)))
        except TypeError:  # /user/<guild_id> returns a list
            pass

        response.set_data(json.dumps(data))

    return response


@api.before_request
def before_request():
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


def format_post_content(guild_id, channel_id, message, dbUser):
    illegal_post = False
    illegal_reasons = []
    message = message.replace("<", "\<")
    message = message.replace(">", "\>")
    message = parse_emoji(message, guild_id)

    dbguild = db.session.query(Guilds).filter(Guilds.guild_id == guild_id).first()

    max_len = get_post_content_max_len(guild_id)
    if len(message) > max_len:
        illegal_post = True
        illegal_reasons.append(
            "Exceeded the following message length: {} characters".format(max_len)
        )

    links = re.findall(
        "http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
        message,
    )
    if not dbguild.chat_links and len(links) > 0:
        illegal_post = True
        illegal_reasons.append("Links is not allowed.")
    elif dbguild.chat_links and not dbguild.bracket_links:
        for link in links:
            newlink = "<" + link + ">"
            message = message.replace(link, newlink)

    mention_pattern = re.compile(r"\[@[0-9]+\]")
    all_mentions = re.findall(mention_pattern, message)
    if dbguild.mentions_limit != -1 and len(all_mentions) > dbguild.mentions_limit:
        illegal_post = True
        illegal_reasons.append(
            "Mentions is capped at the following limit: " + str(dbguild.mentions_limit)
        )

    for match in all_mentions:
        mention = "<@" + match[2 : len(match) - 1] + ">"
        message = message.replace(match, mention, 1)

    if dbguild.banned_words_enabled:
        banned_words = set(json.loads(dbguild.banned_words))
        if dbguild.banned_words_global_included:
            banned_words = banned_words.union(set(constants.GLOBAL_BANNED_WORDS))

        for word in banned_words:
            regex = re.compile(rf"\b{word}\b", re.IGNORECASE)
            if regex.search(message):
                illegal_post = True
                illegal_reasons.append("The following word is prohibited: " + word)

    if not guild_webhooks_enabled(guild_id):
        if session["unauthenticated"]:
            message = f"**[{session['username']}#{session['user_id']}]** {message}"
        else:
            username = session["username"]
            if dbUser and dbUser["nick"]:
                username = dbUser["nick"]

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
    for chan in get_guild_channels(guild_id, force_everyone, get_forced_role(guild_id)):
        if chan["channel"]["id"] == channel_id:
            return chan

    return None


def get_online_discord_users(guild_id, embed):
    apimembers_filtered = {
        int(m["id"]): m for m in redisqueue.list_guild_members(guild_id)
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


def get_online_embed_users(guild_id):
    usrs = redisqueue.get_online_embed_user_keys(guild_id)

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
        usrdb = redisqueue.get_guild_member(guild_id, user.client_id)
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
    return redisqueue.get_guild(guild_id)["emojis"]


def get_guild_roles(guild_id):
    return redisqueue.get_guild(guild_id)["roles"]


# Returns webhook url if exists and can post w/webhooks, otherwise None
def get_channel_webhook_url(guild_id, channel_id):
    if not guild_webhooks_enabled(guild_id):
        return None

    guild = redisqueue.get_guild(guild_id)
    guild_webhooks = guild["webhooks"]
    name = "[Titan] "
    username = session["username"]
    if len(username) > 19:
        username = username[:19]

    if user_unauthenticated():
        name = name + username + "#" + str(session["user_id"])
    else:
        name = name + username + "#" + str(session["discriminator"])

    for webhook in guild_webhooks:
        if channel_id == webhook["channel_id"] and webhook["name"] == name:
            return {
                "id": webhook["id"],
                "token": webhook["token"],
                "name": webhook.get("name"),
                "guild_id": webhook.get("guild_id"),
                "channel_id": webhook.get("channel_id"),
            }

    webhook = discord_api.create_webhook(channel_id, name)
    return webhook.get("content") if webhook else None


def delete_webhook_if_too_much(webhook):
    if not webhook:
        return

    guild_id = webhook["guild_id"]
    if not guild_webhooks_enabled(guild_id):
        return

    guild = redisqueue.get_guild(guild_id)

    titan_wh_cnt = len(
        [wh for wh in guild["webhooks"] if wh["name"].startswith("[Titan] ")]
    )

    if titan_wh_cnt > 0 and len(guild["webhooks"]) >= 8:
        try:
            discord_api.delete_webhook(webhook["id"], webhook["token"])
        except:
            log.exception("Could not delete webhook")
            pass  # not my problem now


def get_all_users(guild_id):
    mem = []
    for u in redisqueue.list_guild_members(guild_id):
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
def fetch():
    guild_id = request.args.get("guild_id")
    channel_id = request.args.get("channel_id")
    after_snowflake = request.args.get("after", 0, type=int)
    key = session["user_keys"][guild_id] if user_unauthenticated() else None
    status = update_user_status(guild_id, session["username"], key)

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
            messages = redisqueue.get_channel_messages(
                guild_id, channel_id, after_snowflake
            )
            status_code = 200

    response = jsonify(messages=messages, status=status)
    response.status_code = status_code

    return response


@api.route("/fetch_visitor", methods=["GET"])
@abort_if_guild_disabled()
@rate_limiter.limit("2 per 2 second", key_func=channel_ratelimit_key)
def fetch_visitor():
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
        messages = redisqueue.get_channel_messages(
            guild_id, channel_id, after_snowflake
        )
        status_code = 200

    response = jsonify(messages=messages)
    response.status_code = status_code

    return response


def get_guild_specific_post_limit():
    guild_id = int_or_none(request.form.get("guild_id", None))

    if guild_id and (
        db_guild := db.session.query(Guilds).filter(Guilds.guild_id == guild_id).first()
    ):
        seconds = db_guild.post_timeout
    else:
        seconds = 5

    return f"1 per {seconds} second"


def get_post_content_max_len(guild_id):
    guild_id = int_or_none(guild_id)

    if guild_id and (
        db_guild := db.session.query(Guilds).filter(Guilds.guild_id == guild_id).first()
    ):
        return db_guild.max_message_length

    return 350


@api.route("/post", methods=["POST"])
@valid_session_required(api=True)
@abort_if_guild_disabled()
@rate_limiter.limit(get_guild_specific_post_limit, key_func=channel_ratelimit_key)
def post():
    guild_id = request.form.get("guild_id")
    channel_id = request.form.get("channel_id")
    content = request.form.get("content", "")

    file = getattr(request.files.get("file"), "filename", None) or None
    rich_embed = json.loads(request.form.get("richembed", "{}"))

    db_user = (
        redisqueue.get_guild_member(guild_id, session["user_id"])
        if "user_id" in session
        else None
    )

    key = session["user_keys"][guild_id] if user_unauthenticated() else None

    content, illegal_post, illegal_reasons = format_post_content(
        guild_id, channel_id, content, db_user
    )
    status = update_user_status(guild_id, session["username"], key)
    message = {}

    if illegal_post:
        status_code = 417
    if status["banned"] or status["revoked"]:
        status_code = 401
    else:
        chan = filter_guild_channel(guild_id, channel_id)
        if not chan.get("write") or chan["channel"]["type"] != "text":
            status_code = 401
        elif (file and not chan.get("attach_files")) or (
            rich_embed and not chan.get("embed_links")
        ):
            status_code = 406
        elif not illegal_post:
            content = format_everyone_mention(chan, content)

            # if userid in get_administrators_list():
            #     content = "(Titan Dev) " + content
            if webhook := get_channel_webhook_url(guild_id, channel_id):
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

                    # if content.startswith("(Titan Dev) "):
                    #     content = content[12:]
                    #     username = "(Titan Dev) " + username

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
                delete_webhook_if_too_much(webhook)
            else:
                message = discord_api.create_message(
                    channel_id, content, file, rich_embed
                )

            status_code = message["code"]

    db.session.commit()
    response = jsonify(
        message=message.get("content", message),
        status=status,
        illegal_reasons=illegal_reasons,
    )
    response.status_code = status_code
    return response


def verify_captcha_request(captcha_response, ip_address):
    payload = {
        "secret": config["recaptcha-secret-key"],
        "response": captcha_response,
        "remoteip": ip_address,
    }
    if app.config["DEBUG"]:
        del payload["remoteip"]

    r = requests.post(
        "https://www.google.com/recaptcha/api/siteverify", data=payload
    ).json()

    return r["success"]


@api.route("/create_unauthenticated_user", methods=["POST"])
@rate_limiter.limit("3 per 30 minute", key_func=guild_ratelimit_key)
@abort_if_guild_disabled()
def create_unauthenticated_user():
    session["unauthenticated"] = True
    username = request.form["username"]
    guild_id = request.form["guild_id"]
    ip_address = get_client_ipaddr()

    username = username.strip()
    if len(username) < 2 or len(username) > 32:
        abort(406)
    if not all(x.isalnum() or x.isspace() or "-" == x or "_" == x for x in username):
        abort(406)
    if not check_guild_existance(guild_id):
        abort(404)
    if not guild_query_unauth_users_bool(guild_id):
        abort(401)

    if guild_unauthcaptcha_enabled(guild_id):
        if not verify_captcha_request(
            request.form["captcha_response"], request.remote_addr
        ):
            abort(412)

    if not checkUserBanned(guild_id, ip_address):
        session["username"] = username
        if "user_id" not in session or len(str(session["user_id"])) > 4:
            session["user_id"] = random.randint(0, 9999)

        user = UnauthenticatedUsers(guild_id, username, session["user_id"], ip_address)
        db.session.add(user)

        key = user.user_key
        if "user_keys" not in session:
            session["user_keys"] = {guild_id: key}
        else:
            session["user_keys"][guild_id] = key

        session.permanent = False

        status = update_user_status(guild_id, username, key)
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
def change_unauthenticated_username():
    username = request.form["username"]
    guild_id = request.form["guild_id"]
    ip_address = get_client_ipaddr()
    username = username.strip()

    if len(username) < 2 or len(username) > 32:
        abort(406)
    if not all(x.isalnum() or x.isspace() or "-" == x or "_" == x for x in username):
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

        user = UnauthenticatedUsers(guild_id, username, session["user_id"], ip_address)
        db.session.add(user)
        key = user.user_key
        session["user_keys"][guild_id] = key
        status = update_user_status(guild_id, username, key)

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
        db.session.query(Guilds).filter(Guilds.guild_id == guild_id).first().guest_icon
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
def query_guild():
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
def query_guild_visitor():
    guild_id = request.args.get("guild_id")

    if not check_guild_existance(guild_id):
        abort(404)
    if not guild_accepts_visitors(guild_id):
        abort(403)

    return process_query_guild(guild_id, True)


@api.route("/server_members", methods=["GET"])
@abort_if_guild_disabled()
@valid_session_required(api=True)
def server_members():
    guild_id = request.args.get("guild_id", None)

    if not check_guild_existance(guild_id):
        abort(404)
    if not check_user_in_guild(guild_id):
        abort(403)

    return jsonify(query_server_members(guild_id))


@api.route("/server_members_visitor", methods=["GET"])
@abort_if_guild_disabled()
def server_members_visitor():
    abort(404)
    guild_id = request.args.get("guild_id", None)

    if not check_guild_existance(guild_id):
        abort(404)
    if not guild_accepts_visitors(guild_id):
        abort(403)

    return jsonify(query_server_members(guild_id))


def query_server_members(guild_id):
    widget = discord_api.get_widget(guild_id)
    if widget.get("success", True):
        discordmembers = get_online_discord_users(guild_id, widget)
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
        "embedmembers": get_online_embed_users(guild_id),
        "widgetenabled": widgetenabled,
    }


@api.route("/create_authenticated_user", methods=["POST"])
@discord_users_only(api=True)
@abort_if_guild_disabled()
def create_authenticated_user():
    if session["unauthenticated"]:
        response = jsonify(error=True)
        response.status_code = 401
        return response

    guild_id = request.form.get("guild_id")
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

    status = update_user_status(guild_id, session["username"])
    return jsonify(status=status)


@api.route("/user/<guild_id>/<user_id>")
@abort_if_guild_disabled()
def user_info(guild_id, user_id):
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

    member = redisqueue.get_guild_member(guild_id, user_id)
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
        guild_roles = redisqueue.get_guild(guild_id)["roles"]
        usr["roles"] = [gr for gr in guild_roles for r in roles if gr["id"] == r]

        usr["badges"] = get_badges(user_id)
        if redisqueue.redis_store.get(f"DiscordBotsOrgVoted/{member['id']}"):
            usr["badges"].append("discordbotsorgvoted")

    return jsonify(usr)


@api.route("/user/<guild_id>")
@abort_if_guild_disabled()
@valid_session_required(api=True)
def list_users(guild_id):
    return jsonify(get_all_users(guild_id))


@api.route("/webhook/discordbotsorg/vote", methods=["POST"])
def webhook_discordbotsorg_vote():
    incoming = request.get_json()
    client_id = incoming.get("bot")

    if str(config["client-id"]) != str(client_id):
        abort(401)

    if str(request.headers.get("Authorization", "")) != str(
        config.get("discordbotsorg-webhook-secret", "")
    ):
        abort(403)

    user_id = incoming.get("user")
    params = dict(parse_qsl(urlsplit(incoming.get("query", "")).query))

    vote_type = str(incoming.get("type"))
    if vote_type == "upvote":
        redisqueue.redis_store.set(f"DiscordBotsOrgVoted/{user_id}", "voted", 86400)

    DBLTrans = DiscordBotsOrgTransactions(
        int(user_id), vote_type, int_or_none(params.get("referrer"))
    )
    db.session.add(DBLTrans)
    db.session.commit()

    return "", 204


@api.route("/bot/ban", methods=["POST"])
def bot_ban():
    if request.headers.get("Authorization", "") != config.get("app-secret", ""):
        return jsonify(error="Authorization header does not match."), 403

    incoming = request.get_json()
    guild_id = incoming.get("guild_id", None)
    placer_id = incoming.get("placer_id", None)
    username = incoming.get("username", None)
    discriminator = incoming.get("discriminator", None)

    if not guild_id or not placer_id or not username:
        return jsonify(error="Missing required parameters."), 400

    dbuser = query_unauthenticated_users_like(username, guild_id, discriminator)
    if not dbuser:
        return jsonify(error="Guest user cannot be found."), 404

    dbban = (
        db.session.query(UnauthenticatedBans)
        .filter(UnauthenticatedBans.guild_id == str(guild_id))
        .filter(UnauthenticatedBans.last_username == dbuser.username)
        .filter(UnauthenticatedBans.last_discriminator == dbuser.discriminator)
        .first()
    )
    if dbban is not None:
        if dbban.lifter_id is None:
            return (
                jsonify(
                    error=f"Guest user, **{dbban.last_username}#{dbban.last_discriminator}**, has already been banned."
                ),
                409,
            )
        db.session.delete(dbban)

    dbban = UnauthenticatedBans(
        str(guild_id),
        dbuser.ip_address,
        dbuser.username,
        dbuser.discriminator,
        "",
        int(placer_id),
    )
    db.session.add(dbban)
    db.session.commit()
    return jsonify(
        success=f"Guest user, **{dbban.last_username}#{dbban.last_discriminator}**, has successfully been added to the ban list!"
    )


@api.route("/bot/unban", methods=["POST"])
def bot_unban():
    if request.headers.get("Authorization", "") != config.get("app-secret", ""):
        return jsonify(error="Authorization header does not match."), 403

    incoming = request.get_json()
    guild_id = incoming.get("guild_id", None)
    lifter_id = incoming.get("lifter_id", None)
    username = incoming.get("username", None)
    discriminator = incoming.get("discriminator", None)

    if not guild_id or not lifter_id or not username:
        return jsonify(error="Missing required parameters."), 400

    dbuser = query_unauthenticated_users_like(username, guild_id, discriminator)
    if not dbuser:
        return jsonify(error="Guest user cannot be found."), 404

    dbban = (
        db.session.query(UnauthenticatedBans)
        .filter(UnauthenticatedBans.guild_id == str(guild_id))
        .filter(UnauthenticatedBans.ip_address == dbuser.ip_address)
        .first()
    )
    if dbban is None:
        return (
            jsonify(
                error=f"Guest user **{dbuser.username}#{dbuser.discriminator}** has not been banned."
            ),
            404,
        )

    if dbban.lifter_id is not None:
        return (
            jsonify(
                error=f"Guest user **{dbuser.username}#{dbuser.discriminator}** ban has already been removed."
            ),
            409,
        )

    dbban.liftBan(int(lifter_id))
    db.session.commit()

    return jsonify(
        success=f"Guest user, **{dbuser.username}#{dbuser.discriminator}**, has successfully been removed from the ban list!"
    )


@api.route("/bot/revoke", methods=["POST"])
def bot_revoke():
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
def bot_members():
    if request.headers.get("Authorization", "") != config.get("app-secret", ""):
        return jsonify(error="Authorization header does not match."), 403

    return jsonify(get_online_embed_users(request.args.get("guild_id")))


@api.route("/af/direct_message", methods=["POST"])
def af_direct_message_post():
    payload = {
        "key": config["cleverbot-api-key"],
        "cs": request.form.get("cs", None),
        "input": request.form.get("input"),
    }
    r = requests.get(CLEVERBOT_URL, params=payload)

    return jsonify(r.json())
