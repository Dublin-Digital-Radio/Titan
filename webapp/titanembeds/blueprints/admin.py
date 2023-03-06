import json
import datetime
import operator
from functools import wraps

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
from titanembeds import redisqueue
from titanembeds.database import (
    ApplicationSettings,
    Cosmetics,
    DisabledGuilds,
    DiscordBotsOrgTransactions,
    Guilds,
    TitanTokens,
    TokenTransactions,
    UnauthenticatedBans,
    UnauthenticatedUsers,
    UserCSS,
    db,
    get_administrators_list,
    get_titan_token,
    list_disabled_guilds,
    set_titan_token,
)
from titanembeds.redisqueue import get_online_embed_user_keys
from titanembeds.utils import generate_guild_icon_url

admin = Blueprint("admin", __name__)


def is_admin(f):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("index"))
            if str(session["user_id"]) not in get_administrators_list():
                return redirect(url_for("index"))
            return f(*args, **kwargs)

        return decorated_function

    return decorator(f)


def get_online_users_count():
    users = get_online_embed_user_keys()
    auths = len(users["AuthenticatedUsers"])
    unauths = len(users["UnauthenticatedUsers"])
    return {"authenticated": auths, "guest": unauths, "total": auths + unauths}


@admin.route("/")
@is_admin
def index():
    return render_template(
        "admin_index.html.j2", count=get_online_users_count()
    )


@admin.route("/cosmetics", methods=["GET"])
@is_admin
def cosmetics():
    entries = db.session.query(Cosmetics).all()
    return render_template("admin_cosmetics.html.j2", cosmetics=entries)


@admin.route("/cosmetics", methods=["POST"])
@is_admin
def cosmetics_post():
    user_id = request.form.get("user_id", None)
    if not user_id:
        abort(400)

    css = request.form.get("css", None)
    css_limit = int(request.form.get("css_limit", 0))
    guest_icon = request.form.get("guest_icon", None)
    send_rich_embed = request.form.get("send_rich_embed", None)
    badges = request.form.get("badges", None)
    entry = (
        db.session.query(Cosmetics).filter(Cosmetics.user_id == user_id).first()
    )
    if entry:
        abort(409)

    user = Cosmetics(user_id)

    if css:
        css = css.lower() == "true"
        user.css = css
    if css_limit is not None:
        user.css_limit = css_limit
    if guest_icon is not None:
        guest_icon = guest_icon.lower() == "true"
        user.guest_icon = guest_icon
    if send_rich_embed:
        send_rich_embed = send_rich_embed.lower() == "true"
        user.send_rich_embed = send_rich_embed
    if badges is not None:
        badges = badges.split(",")
        if badges == [""]:
            badges = []
        user.badges = json.dumps(badges)

    db.session.add(user)
    db.session.commit()

    return "", 204


@admin.route("/cosmetics", methods=["DELETE"])
@is_admin
def cosmetics_delete():
    user_id = request.form.get("user_id", None)
    if not user_id:
        abort(400)

    entry = (
        db.session.query(Cosmetics).filter(Cosmetics.user_id == user_id).first()
    )
    if not entry:
        abort(409)

    db.session.delete(entry)
    db.session.commit()

    return "", 204


@admin.route("/cosmetics", methods=["PATCH"])
@is_admin
def cosmetics_patch():
    user_id = request.form.get("user_id", None)
    if not user_id:
        abort(400)

    css = request.form.get("css", None)
    css_limit = request.form.get("css_limit", None)
    guest_icon = request.form.get("guest_icon", None)
    send_rich_embed = request.form.get("send_rich_embed", None)
    badges = request.form.get("badges", None)

    entry = (
        db.session.query(Cosmetics).filter(Cosmetics.user_id == user_id).first()
    )
    if not entry:
        abort(409)

    if css:
        css = css.lower() == "true"
        entry.css = css
    if css_limit is not None:
        entry.css_limit = css_limit
    if guest_icon:
        guest_icon = guest_icon.lower() == "true"
        entry.guest_icon = guest_icon
    if send_rich_embed:
        send_rich_embed = send_rich_embed.lower() == "true"
        entry.send_rich_embed = send_rich_embed
    if badges is not None:
        badges = badges.split(",")
        if badges == [""]:
            badges = []
        entry.badges = json.dumps(badges)

    db.session.commit()

    return "", 204


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
                    alias = f"{user['username']}#{user['discrim']}"
                    if len(usr["aliases"]) < 5 and alias not in usr["aliases"]:
                        usr["aliases"].append(alias)
                    continue

    return all_users


@admin.route("/administrate_guild/<guild_id>", methods=["GET"])
@is_admin
def administrate_guild(guild_id):
    guild = redisqueue.get_guild(guild_id)
    if not guild:
        abort(404)
        return

    db_guild = (
        db.session.query(Guilds).filter(Guilds.guild_id == guild_id).first()
    )
    if not db_guild:
        db_guild = Guilds(guild["id"])
        db.session.add(db_guild)
        db.session.commit()

    session["redirect"] = None
    cosmetics = (
        db.session.query(Cosmetics)
        .filter(Cosmetics.user_id == session["user_id"])
        .first()
    )

    permissions = []
    permissions.append("Manage Embed Settings")
    permissions.append("Ban Members")
    permissions.append("Kick Members")
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
        "id": guild["id"],
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
        "invite_link": db_guild.invite_link
        if db_guild.invite_link != None
        else "",
        "guest_icon": db_guild.guest_icon
        if db_guild.guest_icon != None
        else "",
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
    )


@admin.route("/administrate_guild/<guild_id>", methods=["POST"])
@is_admin
def update_administrate_guild(guild_id):
    true = ["true", True]

    guild = db.session.query(Guilds).filter(Guilds.guild_id == guild_id).first()
    guild.unauth_users = (
        request.form.get("unauth_users", guild.unauth_users) in true
    )
    guild.visitor_view = (
        request.form.get("visitor_view", guild.visitor_view) in true
    )
    guild.webhook_messages = (
        request.form.get("webhook_messages", guild.webhook_messages) in true
    )

    guild.chat_links = request.form.get("chat_links", guild.chat_links) in true
    guild.bracket_links = (
        request.form.get("bracket_links", guild.bracket_links) in true
    )
    guild.mentions_limit = request.form.get(
        "mentions_limit", guild.mentions_limit
    )
    guild.unauth_captcha = (
        request.form.get("unauth_captcha", guild.unauth_captcha) in true
    )
    guild.post_timeout = request.form.get("post_timeout", guild.post_timeout)
    guild.max_message_length = request.form.get(
        "max_message_length", guild.max_message_length
    )
    guild.banned_words_enabled = (
        request.form.get("banned_words_enabled", guild.banned_words_enabled)
        in true
    )
    guild.banned_words_global_included = (
        request.form.get(
            "banned_words_global_included", guild.banned_words_global_included
        )
        in true
    )
    guild.autorole_unauth = request.form.get(
        "autorole_unauth", guild.autorole_unauth, type=int
    )
    guild.autorole_discord = request.form.get(
        "autorole_discord", guild.autorole_discord, type=int
    )
    guild.file_upload = (
        request.form.get("file_upload", guild.file_upload) in true
    )
    guild.send_rich_embed = (
        request.form.get("send_rich_embed", guild.send_rich_embed) in true
    )
    invite_link = request.form.get("invite_link", guild.invite_link)

    if invite_link is not None and invite_link.strip() == "":
        invite_link = None

    guild.invite_link = invite_link
    guest_icon = request.form.get("guest_icon", guild.guest_icon)
    if guest_icon is not None and guest_icon.strip() == "":
        guest_icon = None
    guild.guest_icon = guest_icon

    banned_word = request.form.get("banned_word", None)
    if banned_word:
        delete_banned_word = (
            request.form.get("delete_banned_word", False) in true
        )
        banned_words = set(json.loads(guild.banned_words))
        if delete_banned_word:
            banned_words.discard(banned_word)
        else:
            banned_words.add(banned_word)
        guild.banned_words = json.dumps(list(banned_words))

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
        guild_id=guild.guild_id,
        unauth_users=guild.unauth_users,
        visitor_view=guild.visitor_view,
        webhook_messages=guild.webhook_messages,
        chat_links=guild.chat_links,
        bracket_links=guild.bracket_links,
        mentions_limit=guild.mentions_limit,
        invite_link=guild.invite_link,
        guest_icon=guild.guest_icon,
        unauth_captcha=guild.unauth_captcha,
        post_timeout=guild.post_timeout,
        max_message_length=guild.max_message_length,
        banned_words_enabled=guild.banned_words_enabled,
        banned_words_global_included=guild.banned_words_global_included,
        banned_words=json.loads(guild.banned_words),
        autorole_unauth=guild.autorole_unauth,
        autorole_discord=guild.autorole_discord,
        file_upload=guild.file_upload,
        send_rich_embed=guild.send_rich_embed,
    )


@admin.route("/guilds")
@is_admin
def guilds():
    guilds = []
    for guild in db.session.query(Guilds).all():
        if not (rguild := redisqueue.get_guild(guild.guild_id)):
            continue
        guilds.append(
            {
                "guild_id": guild.guild_id,
                "name": rguild["name"],
                "icon": rguild["icon"],
            }
        )

    return render_template(
        "admin_guilds.html.j2",
        servers=guilds,
        icon_generate=generate_guild_icon_url,
    )


@admin.route("/tokens", methods=["GET"])
@is_admin
def manage_titan_tokens():
    donators = []
    for usr in db.session.query(TitanTokens).all():
        row = {"user_id": usr.user_id, "tokens": usr.tokens, "transactions": []}
        transact = (
            db.session.query(TokenTransactions)
            .filter(TokenTransactions.user_id == usr.user_id)
            .all()
        )

        for tr in transact:
            row["transactions"].append(
                {
                    "id": tr.id,
                    "user_id": tr.user_id,
                    "timestamp": tr.timestamp,
                    "action": tr.action,
                    "net_tokens": tr.net_tokens,
                    "start_tokens": tr.start_tokens,
                    "end_tokens": tr.end_tokens,
                }
            )
        donators.append(row)

    return render_template(
        "admin_token_transactions.html.j2", donators=donators
    )


@admin.route("/tokens", methods=["POST"])
@is_admin
def post_titan_tokens():
    user_id = request.form.get("user_id", None)
    amount = request.form.get("amount", None, type=int)
    reason = request.form.get("reason", None)

    if not user_id or not amount:
        abort(400)
    if get_titan_token(user_id) != -1:
        abort(409)

    set_titan_token(user_id, amount, f"NEW VIA ADMIN [{str(reason)}]")
    db.session.commit()

    return "", 204


@admin.route("/tokens", methods=["PATCH"])
@is_admin
def patch_titan_tokens():
    user_id = request.form.get("user_id", None)
    amount = request.form.get("amount", None, type=int)
    reason = request.form.get("reason", None)

    if not user_id or not amount:
        abort(400)
    if get_titan_token(user_id) == -1:
        abort(409)

    set_titan_token(user_id, amount, f"MODIFY VIA ADMIN [{str(reason)}]")
    db.session.commit()

    return "", 204


@admin.route("/disabled_guilds", methods=["GET"])
@is_admin
def get_disabled_guilds():
    return render_template(
        "admin_disabled_guilds.html.j2", guilds=list_disabled_guilds()
    )


@admin.route("/disabled_guilds", methods=["POST"])
@is_admin
def post_disabled_guilds():
    guild_id = request.form.get("guild_id", None)
    if guild_id in list_disabled_guilds():
        abort(409)

    guild = DisabledGuilds(guild_id)
    db.session.add(guild)
    db.session.commit()

    return "", 204


@admin.route("/disabled_guilds", methods=["DELETE"])
@is_admin
def delete_disabled_guilds():
    guild_id = request.form.get("guild_id", None)
    if guild_id not in list_disabled_guilds():
        abort(409)

    guild = (
        db.session.query(DisabledGuilds)
        .filter(DisabledGuilds.guild_id == guild_id)
        .first()
    )
    db.session.delete(guild)
    db.session.commit()

    return "", 204


@admin.route("/custom_css", methods=["GET"])
@is_admin
def list_custom_css_get():
    css = db.session.query(UserCSS).order_by(UserCSS.id).all()
    return render_template("admin_usercss.html.j2", css=css)


@admin.route("/custom_css/edit/<css_id>", methods=["GET"])
@is_admin
def edit_custom_css_get(css_id):
    css = db.session.query(UserCSS).filter(UserCSS.id == css_id).first()
    if not css:
        abort(404)

    variables = json.loads(css.css_variables) if css.css_variables else None

    return render_template(
        "usercss.html.j2", new=False, css=css, variables=variables, admin=True
    )


@admin.route("/custom_css/edit/<css_id>", methods=["POST"])
@is_admin
def edit_custom_css_post(css_id):
    dbcss = db.session.query(UserCSS).filter(UserCSS.id == css_id).first()
    if not dbcss:
        abort(404)

    name = request.form.get("name", "").strip() or None
    if not name:
        abort(400)

    dbcss.name = name
    dbcss.user_id = request.form.get("user_id", None) or dbcss.user_id
    dbcss.css = request.form.get("css", "").strip() or None
    dbcss.css_variables = request.form.get("variables", None)
    dbcss.css_var_bool = request.form.get("variables_enabled", False) in [
        "true",
        True,
    ]
    db.session.commit()

    return jsonify({"id": dbcss.id})


@admin.route("/custom_css/edit/<css_id>", methods=["DELETE"])
@is_admin
def edit_custom_css_delete(css_id):
    dbcss = db.session.query(UserCSS).filter(UserCSS.id == css_id).first()
    if not dbcss:
        abort(404)

    db.session.delete(dbcss)
    db.session.commit()

    return jsonify({})


@admin.route("/custom_css/new", methods=["GET"])
@is_admin
def new_custom_css_get():
    return render_template("usercss.html.j2", new=True, admin=True)


@admin.route("/custom_css/new", methods=["POST"])
@is_admin
def new_custom_css_post():
    name = request.form.get("name", None).strip()
    user_id = request.form.get("user_id", None)
    if not name or not user_id:
        abort(400)

    db_css = UserCSS(
        name,
        user_id,
        request.form.get("variables_enabled", False) in ["true", True],
        request.form.get("variables", None),
        request.form.get("css", "").strip() or None,
    )
    db.session.add(db_css)
    db.session.commit()

    return jsonify({"id": db_css.id})


@admin.route("/voting", methods=["GET"])
@is_admin
def voting_get():
    datestart = request.args.get("datestart")
    timestart = request.args.get("timestart")
    dateend = request.args.get("dateend")
    timeend = request.args.get("timeend")

    if not datestart or not timestart or not dateend or not timeend:
        return render_template("admin_voting.html.j2")

    start = datetime.datetime.strptime(
        datestart + " " + timestart, "%d %B, %Y %I:%M%p"
    )
    end = datetime.datetime.strptime(
        dateend + " " + timeend, "%d %B, %Y %I:%M%p"
    )
    users = (
        db.session.query(DiscordBotsOrgTransactions)
        .filter(
            DiscordBotsOrgTransactions.timestamp >= start,
            DiscordBotsOrgTransactions.timestamp <= end,
        )
        .order_by(DiscordBotsOrgTransactions.timestamp)
    )
    all_users = []

    for u in users:
        all_users.append(
            {
                "id": u.id,
                "user_id": u.user_id,
                "timestamp": u.timestamp,
                "action": u.action,
                "referrer": u.referrer,
            }
        )

    overall_votes = {}
    for u in all_users:
        uid = u["user_id"]
        action = u["action"]
        if uid not in overall_votes:
            overall_votes[uid] = 0
        if action == "upvote":
            overall_votes[uid] = overall_votes[uid] + 1

    sorted_overall_votes = [
        u[0]
        for u in sorted(
            overall_votes.items(), key=operator.itemgetter(1), reverse=True
        )
    ]

    overall = []
    for uid in sorted_overall_votes:
        gmember = redisqueue.get_user(uid)
        u = {"user_id": uid, "votes": overall_votes[uid]}
        if gmember:
            u["discord"] = (
                gmember["username"] + "#" + str(gmember["discriminator"])
            )
        overall.append(u)

    referrer = {}
    for u in all_users:
        if not u["referrer"] or u["referrer"] == u["user_id"]:
            continue
        refer = u["referrer"]
        if refer not in referrer:
            referrer[refer] = 0
        referrer[refer] = referrer[refer] + 1

    sorted_referrers = [
        u[0]
        for u in sorted(
            referrer.items(), key=operator.itemgetter(1), reverse=True
        )
    ]

    referrals = []
    for uid in sorted_referrers:
        gmember = redisqueue.get_user(uid)
        u = {"user_id": uid, "votes": referrer[uid]}
        if gmember:
            u["discord"] = (
                gmember["username"] + "#" + str(gmember["discriminator"])
            )
        referrals.append(u)

    return render_template(
        "admin_voting.html.j2",
        overall=overall,
        referrals=referrals,
        datestart=datestart,
        timestart=timestart,
        dateend=dateend,
        timeend=timeend,
    )


@admin.route("/app_settings", methods=["GET"])
@is_admin
def application_settings_get():
    return render_template(
        "admin_application_settings.html.j2",
        settings=(db.session.query(ApplicationSettings).first()),
    )


@admin.route("/app_settings", methods=["POST"])
@is_admin
def application_settings_post():
    settings = db.session.query(ApplicationSettings).first()

    if "donation_goal_progress" in request.form:
        donation_goal_progress = request.form.get("donation_goal_progress")
        settings.donation_goal_progress = int(donation_goal_progress)

    if "donation_goal_total" in request.form:
        donation_goal_total = request.form.get("donation_goal_total")
        settings.donation_goal_total = int(donation_goal_total)

    if "donation_goal_end" in request.form:
        res = None
        donation_goal_end = request.form.get("donation_goal_end")
        if donation_goal_end:
            donation_goal_end = donation_goal_end.split("/")
            month = int(donation_goal_end[0])
            day = int(donation_goal_end[1])
            year = int(donation_goal_end[2])
            res = datetime.date(year, month, day)
        settings.donation_goal_end = res

    db.session.commit()

    return jsonify(
        {
            "donation_goal_progress": settings.donation_goal_progress,
            "donation_goal_total": settings.donation_goal_total,
            "donation_goal_end": settings.donation_goal_end,
        }
    )
