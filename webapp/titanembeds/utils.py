# from raven.contrib.flask import Sentry
import logging

from config import config
from flask import session
from itsdangerous import URLSafeSerializer
from sqlalchemy import and_
from titanembeds import redisqueue
from titanembeds.cache_keys import get_client_ipaddr
from titanembeds.database import (
    AuthenticatedUsers,
    Guilds,
    UnauthenticatedBans,
    UnauthenticatedUsers,
    db,
)
from titanembeds.discord_rest.oauth import (
    AVATAR_BASE_URL,
    BOT_PERMISSIONS,
    GUILD_ICON_URL,
)
from titanembeds.discord_rest.user import (
    check_user_can_administrate_guild,
    user_has_permission,
)

log = logging.getLogger(__name__)

serializer = URLSafeSerializer(config["app-secret"])


def get_guild(guild_id):
    try:
        guild_id = int(guild_id)
    except (TypeError, ValueError):
        return None

    return redisqueue.get_guild(guild_id)


def check_guild_existance(guild_id):
    try:
        guild_id = int(guild_id)
    except (TypeError, ValueError):
        return False

    return bool(redisqueue.get_guild(guild_id))


def guild_accepts_visitors(guild_id):
    dbGuild = Guilds.query.filter_by(guild_id=guild_id).first()
    return dbGuild.visitor_view


def guild_query_unauth_users_bool(guild_id):
    dbGuild = db.session.query(Guilds).filter(Guilds.guild_id == guild_id).first()
    return dbGuild.unauth_users


def user_unauthenticated():
    return session.get("unauthenticated", True)


def checkUserRevoke(guild_id, user_key=None):
    revoked = True  # guilty until proven not revoked
    if user_unauthenticated():
        dbUser = (
            db.session.query(UnauthenticatedUsers)
            .filter(
                UnauthenticatedUsers.guild_id == guild_id,
                UnauthenticatedUsers.user_key == user_key,
            )
            .first()
        )
        if not dbUser:
            return True

        return dbUser.isRevoked()
    else:
        banned = checkUserBanned(guild_id)
        if banned:
            return revoked
        dbUser = redisqueue.get_guild_member(guild_id, session["user_id"])
        return not dbUser


def checkUserBanned(guild_id, ip_address=None):
    banned = True
    if user_unauthenticated():
        dbUser = UnauthenticatedBans.query.filter(
            and_(
                UnauthenticatedBans.guild_id == guild_id,
                UnauthenticatedBans.ip_address == ip_address,
            )
        ).all()

        if not dbUser:
            banned = False
        else:
            for usr in dbUser:
                if usr.lifter_id is not None:
                    banned = False
    else:
        banned = False
        # dbUser = redisqueue.get_guild_member(guild_id, session["user_id"])
        # if not dbUser:
        #    banned = True # TODO: Figure out ban logic with guild member
    return banned


def update_user_status(guild_id, username, user_key=None):
    if user_unauthenticated():
        ip_address = get_client_ipaddr()
        status = {
            "authenticated": False,
            "avatar": None,
            "manage_embed": False,
            "ip_address": ip_address,
            "username": username,
            "nickname": None,
            "user_key": user_key,
            "guild_id": guild_id,
            "user_id": str(session["user_id"]),
            "banned": checkUserBanned(guild_id, ip_address),
            "revoked": checkUserRevoke(guild_id, user_key),
        }

        if status["banned"] or status["revoked"]:
            session["user_keys"].pop(guild_id, None)
            return status

        db_user = UnauthenticatedUsers.query.filter(
            and_(
                UnauthenticatedUsers.guild_id == guild_id,
                UnauthenticatedUsers.user_key == user_key,
            )
        ).first()

        redisqueue.bump_user_presence_timestamp(
            guild_id, "UnauthenticatedUsers", user_key
        )
        if db_user.username != username or db_user.ip_address != ip_address:
            db_user.username = username
            db_user.ip_address = ip_address
            db.session.commit()
    else:
        status = {
            "authenticated": True,
            "avatar": session["avatar"],
            "manage_embed": check_user_can_administrate_guild(guild_id),
            "username": username,
            "nickname": None,
            "discriminator": session["discriminator"],
            "guild_id": guild_id,
            "user_id": str(session["user_id"]),
            "banned": checkUserBanned(guild_id),
            "revoked": checkUserRevoke(guild_id),
        }

        if status["banned"] or status["revoked"]:
            return status

        if dbMember := redisqueue.get_guild_member(guild_id, status["user_id"]):
            status["nickname"] = dbMember["nick"]

        redisqueue.bump_user_presence_timestamp(
            guild_id, "AuthenticatedUsers", status["user_id"]
        )

    return status


def check_user_in_guild(guild_id):
    if user_unauthenticated():
        log.info("checking if unauthenticated user in guild")
        return guild_id in session.get("user_keys", {})

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

    log.info("checking if authenticated user in guild")
    log.info(db_user)
    user_revoked = checkUserRevoke(guild_id)
    log.info("revoked: %s", user_revoked)
    return db_user is not None and not user_revoked


def get_member_roles(guild_id, user_id):
    q = redisqueue.get_guild_member(guild_id, user_id)
    if not q:
        return []
    roles = q["roles"]
    role_converted = []
    for role in roles:
        role_converted.append(str(role))
    return role_converted


def get_guild_channels(guild_id, force_everyone=False, forced_role=0):
    if user_unauthenticated() or force_everyone:
        member_roles = [guild_id]  # equivalent to @everyone role
    else:
        member_roles = get_member_roles(guild_id, session["user_id"])
        if guild_id not in member_roles:
            member_roles.append(guild_id)
    if forced_role:
        member_roles.append(str(forced_role))

    bot_member_roles = get_member_roles(guild_id, config["client-id"])
    if guild_id not in bot_member_roles:
        bot_member_roles.append(guild_id)

    if not (guild := redisqueue.get_guild(guild_id)):
        return []

    db_guild = db.session.query(Guilds).filter(Guilds.guild_id == guild_id).first()
    guild_channels = guild["channels"]
    guild_roles = guild["roles"]
    guild_owner = guild["owner_id"]
    result_channels = []

    for channel in guild_channels:
        if channel["type"] in ["text", "category"]:
            result = get_channel_permission(
                channel,
                guild_id,
                guild_owner,
                guild_roles,
                member_roles,
                str(session.get("user_id")),
            )
            bot_result = get_channel_permission(
                channel,
                guild_id,
                guild_owner,
                guild_roles,
                bot_member_roles,
                config["client-id"],
            )
            if not bot_result["read"]:
                result["read"] = False
            if not bot_result["write"]:
                result["write"] = False
            if not bot_result["mention_everyone"]:
                result["mention_everyone"] = False
            if (
                not bot_result["attach_files"]
                or not db_guild.file_upload
                or not result["write"]
            ):
                result["attach_files"] = False
            if (
                not bot_result["embed_links"]
                or not db_guild.send_rich_embed
                or not result["write"]
            ):
                result["embed_links"] = False
            result_channels.append(result)

    return sorted(result_channels, key=lambda k: k["channel"]["position"])


def get_channel_permission(
    channel,
    guild_id,
    guild_owner,
    guild_roles,
    member_roles,
    user_id=None,
):
    result = {
        "channel": channel,
        "read": False,
        "write": False,
        "mention_everyone": False,
        "attach_files": False,
        "embed_links": False,
    }
    if not user_id:
        user_id = str(session.get("user_id"))
    if guild_owner == user_id:
        result["read"] = True
        result["write"] = True
        result["mention_everyone"] = True
        result["attach_files"] = True
        result["embed_links"] = True
        return result
    channel_perm = 0

    role_positions = {str(role["id"]): role["position"] for role in guild_roles}
    member_roles = sorted(
        member_roles, key=lambda x: role_positions.get(str(x), -1), reverse=True
    )

    # @everyone
    for role in guild_roles:
        if role["id"] == guild_id:
            channel_perm = role["permissions"]
            break

    # User Guild Roles
    for m_role in member_roles:
        for g_role in guild_roles:
            if g_role["id"] == m_role:
                channel_perm |= g_role["permissions"]
                continue

    # If has server administrator permission
    if user_has_permission(channel_perm, 3):
        result["read"] = True
        result["write"] = True
        result["mention_everyone"] = True
        result["attach_files"] = True
        result["embed_links"] = True
        return result

    # Apply @everyone allow/deny first since it's special
    try:
        maybe_everyone = channel["permission_overwrites"][0]
        if maybe_everyone["id"] == guild_id:
            allows = maybe_everyone["allow"]
            denies = maybe_everyone["deny"]
            channel_perm = (channel_perm & ~denies) | allows
            remaining_overwrites = channel["permission_overwrites"][1:]
        else:
            remaining_overwrites = channel["permission_overwrites"]
    except IndexError:
        remaining_overwrites = channel["permission_overwrites"]

    denies = 0
    allows = 0

    # channel specific
    for overwrite in remaining_overwrites:
        if overwrite["type"] == "role" and overwrite["id"] in member_roles:
            denies |= overwrite["deny"]
            allows |= overwrite["allow"]

    channel_perm = (channel_perm & ~denies) | allows

    # member specific
    for overwrite in remaining_overwrites:
        if overwrite["type"] == "member" and overwrite["id"] == str(user_id):
            channel_perm = (channel_perm & ~overwrite["deny"]) | overwrite["allow"]
            break

    result["read"] = user_has_permission(channel_perm, 10)
    result["write"] = user_has_permission(channel_perm, 11)
    result["mention_everyone"] = user_has_permission(channel_perm, 17)
    result["attach_files"] = user_has_permission(channel_perm, 15)
    result["embed_links"] = user_has_permission(channel_perm, 14)

    # If you cant read channel, you cant write in it
    if not user_has_permission(channel_perm, 10):
        result["read"] = False
        result["write"] = False
        result["mention_everyone"] = False
        result["attach_files"] = False
        result["embed_links"] = False

    return result


def get_forced_role(guild_id):
    db_guild = db.session.query(Guilds).filter(Guilds.guild_id == guild_id).first()
    if not session.get("unauthenticated", True):
        return db_guild.autorole_discord

    return db_guild.autorole_unauth


def bot_can_create_webhooks(guild):
    perm = 0

    # @everyone
    for role in guild["roles"]:
        if role["id"] == guild["id"]:
            perm |= role["permissions"]
            continue

    # User Guild Roles
    for m_role in get_member_roles(guild["id"], config["client-id"]):
        for g_role in guild["roles"]:
            if g_role["id"] == m_role:
                perm |= g_role["permissions"]
                continue

    if user_has_permission(perm, 3):  # Admin perms override yes
        return True

    return user_has_permission(perm, 29)


def guild_webhooks_enabled(guild_id):
    db_guild = db.session.query(Guilds).filter(Guilds.guild_id == guild_id).first()
    if not db_guild.webhook_messages:
        return False

    return bot_can_create_webhooks(redisqueue.get_guild(guild_id))


def guild_unauthcaptcha_enabled(guild_id):
    db_guild = db.session.query(Guilds).filter(Guilds.guild_id == guild_id).first()
    return db_guild.unauth_captcha


def is_int(specimen):
    try:
        int(specimen)
        return True
    except (TypeError, ValueError):
        return False


def int_or_none(num):
    try:
        return int(num)
    except (TypeError, ValueError):
        return None


# sentry = Sentry(dsn=config.get("sentry-dsn", None))


def generate_avatar_url(id, av, discrim="0000", allow_animate=False):
    if av:
        suf = "gif" if allow_animate and str(av).startswith("a_") else "png"
        return f"{AVATAR_BASE_URL}{id}/{av}.{suf}"

    default_av = [0, 1, 2, 3, 4]
    avatar_no = default_av[int(discrim) % len(default_av)]
    return f"https://cdn.discordapp.com/embed/avatars/{avatar_no}.png"


def generate_guild_icon_url(id, hash):
    return f"{GUILD_ICON_URL}{id}/{hash}.png"


def generate_bot_invite_url(guild_id):
    return f"https://discordapp.com/oauth2/authorize?&client_id={config['client-id']}&scope=bot&permissions={BOT_PERMISSIONS}&guild_id={guild_id}"
