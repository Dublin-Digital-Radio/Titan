import os
import time
import logging

from flask_socketio import Namespace, disconnect, emit, join_room, leave_room
from quart import session
from titanembeds import bot_http_client, redis_cache
from titanembeds.cache_keys import get_client_ipaddr
from titanembeds.database import db
from titanembeds.discord_rest import discord_api
from titanembeds.utils import (
    check_user_in_guild,
    get_forced_role,
    get_guild_channels,
    guild_accepts_visitors,
    guild_webhooks_enabled,
    serializer,
    update_user_status,
)
from functools import wraps

DISCORDAPP_AVATARS_URL = "https://cdn.discordapp.com/avatars/"

log = logging.getLogger(__name__)


def teardown_db_session(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        func(*args, **kwargs)
        db.session.commit()
        db.session.remove()

    return wrapped


def check_guild_in_session(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        if "socket_guild_id" not in session:
            log.info("disconnect because socket_guild_id not in session:")
            disconnect()
            return

        return func(*args, **kwargs)

    return wrapped


class Gateway(Namespace):
    def on_connect(self):
        gateway_identifier = os.environ.get("TITAN_GATEWAY_ID", None)
        emit("hello", {"gateway_identifier": gateway_identifier})

    @teardown_db_session
    def on_identify(self, data):
        if authorization := data.get("session", None):
            try:
                session.update(serializer.loads(authorization))
            except:
                log.exception("exception in authorisation session update")
                pass

        guild_id = data["guild_id"]
        if not guild_accepts_visitors(guild_id) and not check_user_in_guild(
            guild_id
        ):
            log.info("not guild_accepts_visitors and not check_user_in_guild")
            return

        session["socket_guild_id"] = guild_id

        force_everyone = guild_accepts_visitors(
            guild_id
        ) and not check_user_in_guild(guild_id)
        channels = get_guild_channels(
            guild_id,
            force_everyone=force_everyone,
            forced_role=get_forced_role(guild_id),
        )

        join_room("GUILD_" + guild_id)
        for chan in channels:
            if chan["read"]:
                join_room("CHANNEL_" + chan["channel"]["id"])

        if session.get("unauthenticated", True) and guild_id in session.get(
            "user_keys", {}
        ):
            join_room(f"IP_{get_client_ipaddr()}")
        elif not session.get("unauthenticated", True):
            join_room(f"USER_{session['user_id']}")

        visitor_mode = data["visitor_mode"]
        if not visitor_mode:
            if session["unauthenticated"]:
                data = {
                    "unauthenticated": True,
                    "username": session["username"],
                    "discriminator": session["user_id"],
                }
            else:
                nickname = bot_http_client.get_guild_member(
                    guild_id, session["user_id"]
                ).get("nickname")
                data = {
                    "unauthenticated": False,
                    "id": str(session["user_id"]),
                    "nickname": nickname,
                    "username": session["username"],
                    "discriminator": session["discriminator"],
                    "avatar_url": session["avatar"],
                }
            emit("embed_user_connect", data, room="GUILD_" + guild_id)

        emit("identified")

    @teardown_db_session
    async def on_disconnect(self):
        if "user_keys" not in session or "socket_guild_id" not in session:
            return

        guild_id = session["socket_guild_id"]

        if session["unauthenticated"]:
            msg = {
                "unauthenticated": True,
                "username": session["username"],
                "discriminator": session["user_id"],
            }
        else:
            msg = {"unauthenticated": False, "id": str(session["user_id"])}
        emit("embed_user_disconnect", msg, room="GUILD_" + guild_id)

        if guild_webhooks_enabled(guild_id):  # Delete webhooks
            guild_webhooks = bot_http_client.get_guild(guild_id)["webhooks"]

            d = (
                session["user_id"]
                if session["unauthenticated"]
                else session["discriminator"]
            )
            name = f"[Titan] {session['username'][:19]}#{d}"

            for webhook in [w for w in guild_webhooks if w["name"] == name]:
                await discord_api.delete_webhook(
                    webhook["id"], webhook["token"], guild_id
                )

    @teardown_db_session
    @check_guild_in_session
    async def on_heartbeat(self, data):
        guild_id = data["guild_id"]
        visitor_mode = data["visitor_mode"]
        if not visitor_mode:
            key = None
            if "unauthenticated" not in session:
                log.info(
                    "disconnect because unauthenticated not in session and not visitor_mode"
                )
                disconnect()
                return

            if session["unauthenticated"]:
                key = session["user_keys"][guild_id]

            status = await update_user_status(
                guild_id, session["username"], key
            )
            if status["revoked"] or status["banned"]:
                emit("revoke")
                time.sleep(1)

                log.info("disconnect because status revoked or banned")
                disconnect()
                return
            else:
                emit("ack")
        else:
            if not guild_accepts_visitors(guild_id):
                log.info("disconnect because guild does no accept visitors")
                disconnect()
                return

    @teardown_db_session
    @check_guild_in_session
    def on_channel_list(self, data):
        guild_id = data["guild_id"]
        forced_role = get_forced_role(guild_id)
        force_everyone = data["visitor_mode"] or session.get(
            "unauthenticated", True
        )
        channels = get_guild_channels(
            guild_id, force_everyone, forced_role=forced_role
        )

        for chan in channels:
            if chan["read"]:
                join_room("CHANNEL_" + chan["channel"]["id"])
            else:
                leave_room("CHANNEL_" + chan["channel"]["id"])

        emit("channel_list", channels)

    @teardown_db_session
    @check_guild_in_session
    def on_current_user_info(self, data):
        guild_id = data["guild_id"]
        if "user_keys" in session and not session["unauthenticated"]:
            db_member = bot_http_client.get_guild_member(
                guild_id, session["user_id"]
            )
            usr = {
                "avatar": session["avatar"],
                "username": db_member.get("username"),
                "nickname": db_member.get("nickname"),
                "discriminator": db_member.get("discriminator"),
                "user_id": str(session["user_id"]),
            }
            emit("current_user_info", usr)

    def get_user_color(self, guild_id, user_id):
        if not (member := bot_http_client.get_guild_member(guild_id, user_id)):
            return None

        # get the role objects from id's in member["roles"]
        guild_roles = bot_http_client.get_guild(guild_id)["roles"]
        roles_map = {str(role["id"]): role for role in guild_roles}
        roles = [
            r for r_id in member["roles"] if (r := roles_map.get(str(r_id)))
        ]

        color = None
        for role in [
            x
            for x in sorted(roles, key=lambda k: k["position"])
            if x["color"] != 0
        ]:
            color = f"{role['color']:02x}"
            while len(color) < 6:
                color = "0" + color

        return color

    @teardown_db_session
    @check_guild_in_session
    def on_lookup_user_info(self, data):
        guild_id = data["guild_id"]
        name = data["name"]
        discriminator = data["discriminator"]
        usr = {
            "name": name,
            "id": None,
            "username": None,
            "nickname": None,
            "discriminator": discriminator,
            "avatar": None,
            "color": None,
            "avatar_url": None,
            "discordbotsorgvoted": False,
        }

        member = bot_http_client.get_guild_member_named(
            guild_id, f"{name}#{discriminator}"
        )
        if member:
            usr["id"] = str(member["id"])
            usr["username"] = member["username"]
            usr["nickname"] = member["nick"]
            usr["avatar"] = member["avatar"]
            usr["color"] = self.get_user_color(guild_id, usr["id"])
            if usr["avatar"]:
                usr[
                    "avatar_url"
                ] = f"{DISCORDAPP_AVATARS_URL}{usr['id']}/{usr['avatar']}.png"
            usr["roles"] = member["roles"]
            usr["discordbotsorgvoted"] = bool(
                redis_cache.redis_store.get(
                    f"DiscordBotsOrgVoted/{member['id']}"
                )
            )
        else:
            member = bot_http_client.get_guild_member_named(guild_id, name)
            if member:
                usr["id"] = str(member["id"])
                usr["username"] = member["username"]
                usr["nickname"] = member["nick"]
                usr["avatar"] = member["avatar"]
                usr["color"] = self.get_user_color(guild_id, usr["id"])
                if usr["avatar"]:
                    usr[
                        "avatar_url"
                    ] = f"{DISCORDAPP_AVATARS_URL}{usr['id']}/{usr['avatar']}.png"
                usr["roles"] = member["roles"]
                usr["discordbotsorgvoted"] = bool(
                    redis_cache.redis_store.get(
                        f"DiscordBotsOrgVoted/{member['id']}"
                    )
                )

        emit("lookup_user_info", usr)
