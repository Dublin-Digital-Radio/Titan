import json
import logging
from pprint import pformat

from flask import (
    Blueprint,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_socketio import emit
from titanembeds.database import (
    Cosmetics,
    Guilds,
    UnauthenticatedBans,
    UnauthenticatedUsers,
    UserCSS,
    db,
    get_titan_token,
    list_disabled_guilds,
)
from titanembeds.decorators import discord_users_only
from titanembeds.discord_rest.oauth import (
    PERMISSION_BAN,
    PERMISSION_KICK,
    PERMISSION_MANAGE,
    get_authorization_url,
    get_token,
)
from titanembeds.discord_rest.user import (
    check_user_can_administrate_guild,
    check_user_permission,
    get_current_authenticated_user,
    get_user_managed_servers,
)
from titanembeds.utils import (
    generate_avatar_url,
    generate_bot_invite_url,
    generate_guild_icon_url,
    redisqueue,
)

log = logging.getLogger(__name__)
user_bp = Blueprint("user", __name__)


@user_bp.route("/login_authenticated", methods=["GET"])
def login_authenticated():
    session["redirect"] = request.args.get("redirect")
    authorization_url, state = get_authorization_url(["identify", "guilds", "guilds.join"])
    session["oauth2_state"] = state

    return redirect(authorization_url)


@user_bp.route("/callback", methods=["GET"])
def callback():
    if not (state := session.get("oauth2_state")):
        return redirect(url_for("user.logout", error="state_error"))

    if request.values.get("error"):
        return redirect(
            url_for(
                "user.logout",
                error="discord_error {}".format(request.values.get("error")),
            )
        )

    if not (discord_token := get_token(state)):
        return redirect(url_for("user.logout", error="discord_user_token_fetch_error"))

    session["user_keys"] = discord_token
    session["unauthenticated"] = False
    session.permanent = True

    user = get_current_authenticated_user()

    session["user_id"] = int(user["id"])
    session["username"] = user["username"]
    session["discriminator"] = user["discriminator"]
    session["avatar"] = generate_avatar_url(user["id"], user["avatar"], user["discriminator"])

    session["tokens"] = get_titan_token(session["user_id"])
    if session["tokens"] == -1:
        session["tokens"] = 0

    log.info("Callback ok. Session: %s", pformat(session))

    if session["redirect"]:
        session["redirect"] = None
        return redirect(session["redirect"])

    return redirect(url_for("user.dashboard"))


@user_bp.route("/logout", methods=["GET"])
def logout():
    session.clear()
    if redir := session.get("redirect", None) or request.args.get("redirect", None):
        session["redirect"] = redir
        return redirect(session["redirect"])

    return redirect(url_for("index"))


def count_user_premium_css():
    css_list = db.session.query(UserCSS).filter(UserCSS.user_id == session["user_id"]).all()
    return len([css for css in css_list if css.css is not None])


@user_bp.route("/dashboard")
@discord_users_only()
def dashboard():
    error = request.args.get("error")
    if session["redirect"] and not (error and error == "access_denied"):
        redir = session["redirect"]
        session["redirect"] = None
        return redirect(redir)

    cosmetics = (
        db.session.query(Cosmetics).filter(Cosmetics.user_id == session["user_id"]).first()
    )

    if cosmetics and cosmetics.css:
        css_list = (
            db.session.query(UserCSS)
            .filter(UserCSS.user_id == session["user_id"])
            .order_by(UserCSS.id)
            .all()
        )
    else:
        css_list = None

    return render_template(
        "dashboard.html.j2",
        servers=get_user_managed_servers(),
        icon_generate=generate_guild_icon_url,
        cosmetics=cosmetics,
        css_list=css_list,
        premium_css_count=count_user_premium_css(),
    )


@user_bp.route("/custom_css/new", methods=["GET"])
@discord_users_only()
def new_custom_css_get():
    cosmetics = (
        db.session.query(Cosmetics).filter(Cosmetics.user_id == session["user_id"]).first()
    )
    if not cosmetics or not cosmetics.css:
        abort(403)

    return render_template(
        "usercss.html.j2",
        new=True,
        cosmetics=cosmetics,
        premium_css_count=count_user_premium_css(),
    )


@user_bp.route("/custom_css/new", methods=["POST"])
@discord_users_only()
def new_custom_css_post():
    cosmetics = (
        db.session.query(Cosmetics).filter(Cosmetics.user_id == session["user_id"]).first()
    )
    if not cosmetics or not cosmetics.css:
        abort(403)

    name = request.form.get("name", "").strip()
    user_id = session["user_id"]
    css = request.form.get("css", "").strip() or None
    variables = request.form.get("variables", None)
    variables_enabled = request.form.get("variables_enabled", False) in ["true", True]

    if not name:
        abort(400)

    db_css = UserCSS(name, user_id, variables_enabled, variables, css)
    db.session.add(db_css)
    db.session.commit()

    return jsonify({"id": db_css.id})


@user_bp.route("/custom_css/edit/<css_id>", methods=["GET"])
@discord_users_only()
def edit_custom_css_get(css_id):
    cosmetics = (
        db.session.query(Cosmetics).filter(Cosmetics.user_id == session["user_id"]).first()
    )
    if not cosmetics or not cosmetics.css:
        abort(403)

    css = db.session.query(UserCSS).filter(UserCSS.id == css_id).first()
    if not css:
        abort(404)
    if str(css.user_id) != str(session["user_id"]):
        abort(403)

    return render_template(
        "usercss.html.j2",
        new=False,
        css=css,
        variables=json.loads(css.css_variables) if css.css_variables else None,
        cosmetics=cosmetics,
        premium_css_count=count_user_premium_css(),
    )


@user_bp.route("/custom_css/edit/<css_id>", methods=["POST"])
@discord_users_only()
def edit_custom_css_post(css_id):
    cosmetics = (
        db.session.query(Cosmetics).filter(Cosmetics.user_id == session["user_id"]).first()
    )
    if not cosmetics or not cosmetics.css:
        abort(403)

    db_css = db.session.query(UserCSS).filter(UserCSS.id == css_id).first()
    if not db_css:
        abort(404)

    if db_css.user_id != session["user_id"]:
        abort(403)

    if not (name := request.form.get("name", "").strip()):
        abort(400)

    db_css.name = name
    db_css.css = request.form.get("css", "").strip() or None
    db_css.css_variables = request.form.get("variables", None)
    db_css.css_var_bool = request.form.get("variables_enabled", False) in ["true", True]
    db.session.commit()

    return jsonify({"id": db_css.id})


@user_bp.route("/custom_css/edit/<css_id>", methods=["DELETE"])
@discord_users_only()
def edit_custom_css_delete(css_id):
    cosmetics = (
        db.session.query(Cosmetics).filter(Cosmetics.user_id == session["user_id"]).first()
    )
    if not cosmetics or not cosmetics.css:
        abort(403)

    db_css = db.session.query(UserCSS).filter(UserCSS.id == css_id).first()
    if not db_css:
        abort(404)
    if db_css.user_id != session["user_id"]:
        abort(403)
    db.session.delete(db_css)
    db.session.commit()

    return jsonify({})


@user_bp.route("/administrate_guild/<guild_id>", methods=["GET"])
@discord_users_only()
def administrate_guild(guild_id):
    if not check_user_can_administrate_guild(guild_id):
        return redirect(url_for("user.dashboard"))

    guild = redisqueue.get_guild(guild_id)
    if not guild:
        session["redirect"] = url_for(
            "user.administrate_guild",
            guild_id=guild_id,
            _external=True,
            _scheme="https",
        )
        return redirect(url_for("user.add_bot", guild_id=guild_id))
    session["redirect"] = None

    db_guild = db.session.query(Guilds).filter(Guilds.guild_id == guild_id).first()
    if not db_guild:
        db_guild = Guilds(guild["id"])
        db.session.add(db_guild)
        db.session.commit()

    permissions = []
    if check_user_permission(guild_id, PERMISSION_MANAGE):
        permissions.append("Manage Embed Settings")
    if check_user_permission(guild_id, PERMISSION_BAN):
        permissions.append("Ban Members")
    if check_user_permission(guild_id, PERMISSION_KICK):
        permissions.append("Kick Members")

    cosmetics = (
        db.session.query(Cosmetics).filter(Cosmetics.user_id == session["user_id"]).first()
    )
    all_members = (
        db.session.query(UnauthenticatedUsers)
        .filter(UnauthenticatedUsers.guild_id == guild_id)
        .order_by(UnauthenticatedUsers.id)
        .limit(2000)
        .all()
    )
    all_bans = (
        db.session.query(UnauthenticatedBans)
        .filter(UnauthenticatedBans.guild_id == guild_id)
        .all()
    )
    users = prepare_guild_members_list(all_members, all_bans)
    dbguild_dict = {
        "id": db_guild.guild_id,
        "name": guild["name"],
        "roles": guild["roles"],
        "unauth_users": db_guild.unauth_users,
        "visitor_view": db_guild.visitor_view,
        "webhook_messages": db_guild.webhook_messages,
        "chat_links": db_guild.chat_links,
        "bracket_links": db_guild.bracket_links,
        "mentions_limit": db_guild.mentions_limit,
        "unauth_captcha": db_guild.unauth_captcha,
        "icon": guild["icon"],
        "invite_link": db_guild.invite_link if db_guild.invite_link is not None else "",
        "guest_icon": db_guild.guest_icon if db_guild.guest_icon is not None else "",
        "post_timeout": db_guild.post_timeout,
        "max_message_length": db_guild.max_message_length,
        "banned_words_enabled": db_guild.banned_words_enabled,
        "banned_words_global_included": db_guild.banned_words_global_included,
        "banned_words": json.loads(db_guild.banned_words),
        "autorole_unauth": db_guild.autorole_unauth,
        "autorole_discord": db_guild.autorole_discord,
        "file_upload": db_guild.file_upload,
        "send_rich_embed": db_guild.send_rich_embed,
    }

    return render_template(
        "administrate_guild.html.j2",
        guild=dbguild_dict,
        members=users,
        permissions=permissions,
        cosmetics=cosmetics,
        disabled=(guild_id in list_disabled_guilds()),
    )


@user_bp.route("/administrate_guild/<guild_id>", methods=["POST"])
@discord_users_only()
def update_administrate_guild(guild_id):
    if guild_id in list_disabled_guilds():
        return "", 423
    if not check_user_can_administrate_guild(guild_id):
        abort(403)
    db_guild = db.session.query(Guilds).filter(Guilds.guild_id == guild_id).first()
    if not db_guild:
        abort(400)
    if not check_user_permission(guild_id, PERMISSION_MANAGE):
        abort(403)

    true = ["true", True]
    db_guild.unauth_users = request.form.get("unauth_users", db_guild.unauth_users) in true
    db_guild.visitor_view = request.form.get("visitor_view", db_guild.visitor_view) in true
    db_guild.webhook_messages = (
        request.form.get("webhook_messages", db_guild.webhook_messages) in true
    )
    db_guild.chat_links = request.form.get("chat_links", db_guild.chat_links) in true
    db_guild.bracket_links = request.form.get("bracket_links", db_guild.bracket_links) in true
    db_guild.mentions_limit = request.form.get("mentions_limit", db_guild.mentions_limit)
    db_guild.unauth_captcha = request.form.get("unauth_captcha", db_guild.unauth_captcha) in true
    db_guild.post_timeout = request.form.get("post_timeout", db_guild.post_timeout)
    db_guild.max_message_length = request.form.get(
        "max_message_length", db_guild.max_message_length
    )
    db_guild.banned_words_enabled = (
        request.form.get("banned_words_enabled", db_guild.banned_words_enabled) in true
    )
    db_guild.banned_words_global_included = (
        request.form.get("banned_words_global_included", db_guild.banned_words_global_included)
        in true
    )
    db_guild.autorole_unauth = request.form.get(
        "autorole_unauth", db_guild.autorole_unauth, type=int
    )
    db_guild.autorole_discord = request.form.get(
        "autorole_discord", db_guild.autorole_discord, type=int
    )
    db_guild.file_upload = request.form.get("file_upload", db_guild.file_upload) in true
    db_guild.send_rich_embed = (
        request.form.get("send_rich_embed", db_guild.send_rich_embed) in true
    )

    invite_link = request.form.get("invite_link", db_guild.invite_link)
    if invite_link is not None and invite_link.strip() == "":
        invite_link = None
    db_guild.invite_link = invite_link

    guest_icon = request.form.get("guest_icon", db_guild.guest_icon)
    if guest_icon is not None and guest_icon.strip() == "":
        guest_icon = None
    db_guild.guest_icon = guest_icon

    banned_word = request.form.get("banned_word", None)
    if banned_word:
        delete_banned_word = request.form.get("delete_banned_word", False) in true
        banned_words = set(json.loads(db_guild.banned_words))
        if delete_banned_word:
            banned_words.discard(banned_word)
        else:
            banned_words.add(banned_word)
        db_guild.banned_words = json.dumps(list(banned_words))

    db.session.commit()
    emit(
        "guest_icon_change",
        {
            "guest_icon": guest_icon
            if guest_icon
            else url_for("static", filename="img/titanembeds_square.png")
        },
        room="GUILD_" + guild_id,
        namespace="/gateway",
    )

    return jsonify(
        guild_id=db_guild.guild_id,
        unauth_users=db_guild.unauth_users,
        visitor_view=db_guild.visitor_view,
        webhook_messages=db_guild.webhook_messages,
        chat_links=db_guild.chat_links,
        bracket_links=db_guild.bracket_links,
        mentions_limit=db_guild.mentions_limit,
        invite_link=db_guild.invite_link,
        guest_icon=guest_icon,
        unauth_captcha=db_guild.unauth_captcha,
        post_timeout=db_guild.post_timeout,
        max_message_length=db_guild.max_message_length,
        banned_words_enabled=db_guild.banned_words_enabled,
        banned_words_global_included=db_guild.banned_words_global_included,
        banned_words=json.loads(db_guild.banned_words),
        autorole_unauth=db_guild.autorole_unauth,
        autorole_discord=db_guild.autorole_discord,
        file_upload=db_guild.file_upload,
        send_rich_embed=db_guild.send_rich_embed,
    )


@user_bp.route("/add-bot/<guild_id>")
@discord_users_only()
def add_bot(guild_id):
    session["redirect"] = None
    return render_template(
        "add_bot.html.j2",
        guild_id=guild_id,
        guild_invite_url=generate_bot_invite_url(guild_id),
    )


def prepare_guild_members_list(members, bans):
    all_users = []
    ip_pool = []
    for member in sorted(members, key=lambda k: k.id, reverse=True):
        user = {
            "id": member.id,
            "username": member.username,
            "discrim": member.discriminator,
            "ip": member.ip_address,
            "kicked": member.revoked,
            "banned": False,
            "banned_timestamp": None,
            "banned_by": None,
            "banned_reason": None,
            "ban_lifted_by": None,
            "aliases": [],
        }

        for banned in bans:
            if banned.ip_address == member.ip_address:
                if banned.lifter_id is None:
                    user["banned"] = True
                user["banned_timestamp"] = banned.timestamp
                user["banned_by"] = banned.placer_id
                user["banned_reason"] = banned.reason
                user["ban_lifted_by"] = banned.lifter_id
            continue

        if user["ip"] not in ip_pool:
            all_users.append(user)
            ip_pool.append(user["ip"])
        else:
            for usr in all_users:
                if user["ip"] == usr["ip"]:
                    alias = f'{user["username"]}#{user["discrim"]}'
                    if len(usr["aliases"]) < 5 and alias not in usr["aliases"]:
                        usr["aliases"].append(alias)
                    continue

    return all_users


@user_bp.route("/ban", methods=["POST"])
@discord_users_only(api=True)
def ban_unauthenticated_user():
    guild_id = request.form.get("guild_id", None)
    user_id = request.form.get("user_id", None)
    reason = request.form.get("reason", None)

    if guild_id in list_disabled_guilds():
        return "", 423

    if reason is not None:
        reason = reason.strip()
        if reason == "":
            reason = None

    if not guild_id or not user_id:
        abort(400)
    if not check_user_permission(guild_id, PERMISSION_BAN):
        abort(401)

    db_user = (
        db.session.query(UnauthenticatedUsers)
        .filter(
            UnauthenticatedUsers.guild_id == guild_id,
            UnauthenticatedUsers.id == user_id,
        )
        .order_by(UnauthenticatedUsers.id.desc())
        .first()
    )
    if db_user is None:
        abort(404)

    db_ban = (
        db.session.query(UnauthenticatedBans)
        .filter(
            UnauthenticatedBans.guild_id == guild_id,
            UnauthenticatedBans.ip_address == db_user.ip_address,
        )
        .first()
    )
    if db_ban is not None:
        if db_ban.lifter_id is None:
            abort(409)
        db.session.delete(db_ban)

    db_ban = UnauthenticatedBans(
        guild_id,
        db_user.ip_address,
        db_user.username,
        db_user.discriminator,
        reason,
        session["user_id"],
    )
    db.session.add(db_ban)
    db.session.commit()

    return "", 204


@user_bp.route("/ban", methods=["DELETE"])
@discord_users_only(api=True)
def unban_unauthenticated_user():
    guild_id = request.args.get("guild_id", None)
    user_id = request.args.get("user_id", None)

    if guild_id in list_disabled_guilds():
        return "", 423
    if not guild_id or not user_id:
        abort(400)
    if not check_user_permission(guild_id, PERMISSION_BAN):
        abort(401)

    db_user = (
        db.session.query(UnauthenticatedUsers)
        .filter(
            UnauthenticatedUsers.guild_id == guild_id,
            UnauthenticatedUsers.id == user_id,
        )
        .order_by(UnauthenticatedUsers.id.desc())
        .first()
    )
    if db_user is None:
        abort(404)

    db_ban = (
        db.session.query(UnauthenticatedBans)
        .filter(
            UnauthenticatedBans.guild_id == guild_id,
            UnauthenticatedBans.ip_address == db_user.ip_address,
        )
        .first()
    )
    if db_ban is None:
        abort(404)
    if db_ban.lifter_id is not None:
        abort(409)

    db_ban.lift_ban(session["user_id"])
    db.session.commit()

    return "", 204


@user_bp.route("/revoke", methods=["POST"])
@discord_users_only(api=True)
def revoke_unauthenticated_user():
    guild_id = request.form.get("guild_id", None)
    user_id = request.form.get("user_id", None)

    if guild_id in list_disabled_guilds():
        return "", 423
    if not guild_id or not user_id:
        abort(400)
    if not check_user_permission(guild_id, PERMISSION_KICK):
        abort(401)

    db_user = (
        db.session.query(UnauthenticatedUsers)
        .filter(
            UnauthenticatedUsers.guild_id == guild_id,
            UnauthenticatedUsers.id == user_id,
        )
        .order_by(UnauthenticatedUsers.id.desc())
        .first()
    )
    if db_user is None:
        abort(404)
    if db_user.isRevoked():
        abort(409)

    db_user.revokeUser()
    db.session.commit()

    return "", 204
