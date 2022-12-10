import os
import time
import logging

from flask import session
from flask_socketio import Namespace, disconnect, emit, join_room, leave_room
from titanembeds import redisqueue
from titanembeds.cache_keys import get_client_ipaddr
from titanembeds.database import db
from titanembeds.discord_rest import discord_api
from titanembeds.utils import (
    check_user_in_guild,
    get_forced_role,
    get_guild_channels,
    guild_accepts_visitors,
    guild_webhooks_enabled,
    redisqueue,
    serializer,
    update_user_status,
)

log = logging.getLogger(__name__)


class Gateway(Namespace):
    def teardown_db_session(self):
        db.session.commit()
        db.session.remove()

    def on_connect(self):
        gateway_identifier = os.environ.get("TITAN_GATEWAY_ID", None)
        emit("hello", {"gateway_identifier": gateway_identifier})

    def on_identify(self, data):
        authorization = data.get("session", None)
        if authorization:
            try:
                data = serializer.loads(authorization)
                session.update(data)
            except:
                log.exception("exception in authorisation session update")
                pass

        guild_id = data["guild_id"]
        if not guild_accepts_visitors(guild_id) and not check_user_in_guild(guild_id):
            disconnect()
            self.teardown_db_session()
            return

        session["socket_guild_id"] = guild_id
        forced_role = get_forced_role(guild_id)
        if guild_accepts_visitors(guild_id) and not check_user_in_guild(guild_id):
            channels = get_guild_channels(guild_id, force_everyone=True, forced_role=forced_role)
        else:
            channels = get_guild_channels(guild_id, forced_role=forced_role)

        join_room("GUILD_" + guild_id)
        for chan in channels:
            if chan["read"]:
                join_room("CHANNEL_" + chan["channel"]["id"])

        if session.get("unauthenticated", True) and guild_id in session.get("user_keys", {}):
            join_room("IP_" + get_client_ipaddr())
        elif not session.get("unauthenticated", True):
            join_room("USER_" + str(session["user_id"]))

        visitor_mode = data["visitor_mode"]
        if not visitor_mode:
            if session["unauthenticated"]:
                emit(
                    "embed_user_connect",
                    {
                        "unauthenticated": True,
                        "username": session["username"],
                        "discriminator": session["user_id"],
                    },
                    room="GUILD_" + guild_id,
                )
            else:
                nickname = redisqueue.get_guild_member(guild_id, session["user_id"]).get(
                    "nickname"
                )
                emit(
                    "embed_user_connect",
                    {
                        "unauthenticated": False,
                        "id": str(session["user_id"]),
                        "nickname": nickname,
                        "username": session["username"],
                        "discriminator": session["discriminator"],
                        "avatar_url": session["avatar"],
                    },
                    room="GUILD_" + guild_id,
                )

        emit("identified")
        self.teardown_db_session()

    def on_disconnect(self):
        if "user_keys" not in session or "socket_guild_id" not in session:
            self.teardown_db_session()
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
            guild_webhooks = redisqueue.get_guild(guild_id)["webhooks"]

            username = session["username"]
            if len(username) > 19:
                username = username[:19]

            d = session["user_id"] if session["unauthenticated"] else session["discriminator"]
            name = f"[Titan] {username}#{d}"

            for webhook in guild_webhooks:
                if webhook["name"] == name:
                    discord_api.delete_webhook(webhook["id"], webhook["token"])

        self.teardown_db_session()

    def on_heartbeat(self, data):
        if "socket_guild_id" not in session:
            disconnect()
            return

        guild_id = data["guild_id"]
        visitor_mode = data["visitor_mode"]
        if not visitor_mode:
            key = None
            if "unauthenticated" not in session:
                self.teardown_db_session()
                disconnect()
                return

            if session["unauthenticated"]:
                key = session["user_keys"][guild_id]

            status = update_user_status(guild_id, session["username"], key)
            if status["revoked"] or status["banned"]:
                emit("revoke")
                self.teardown_db_session()
                time.sleep(1)
                disconnect()
                return
            else:
                emit("ack")
        else:
            if not guild_accepts_visitors(guild_id):
                self.teardown_db_session()
                disconnect()
                return

        self.teardown_db_session()

    def on_channel_list(self, data):
        if "socket_guild_id" not in session:
            disconnect()
            return

        guild_id = data["guild_id"]
        forced_role = get_forced_role(guild_id)
        force_everyone = data["visitor_mode"] or session.get("unauthenticated", True)
        channels = get_guild_channels(guild_id, force_everyone, forced_role=forced_role)

        for chan in channels:
            if chan["read"]:
                join_room("CHANNEL_" + chan["channel"]["id"])
            else:
                leave_room("CHANNEL_" + chan["channel"]["id"])

        emit("channel_list", channels)
        self.teardown_db_session()

    def on_current_user_info(self, data):
        if "socket_guild_id" not in session:
            disconnect()
            return

        guild_id = data["guild_id"]
        if "user_keys" in session and not session["unauthenticated"]:
            dbMember = redisqueue.get_guild_member(guild_id, session["user_id"])
            usr = {
                "avatar": session["avatar"],
                "username": dbMember.get("username"),
                "nickname": dbMember.get("nickname"),
                "discriminator": dbMember.get("discriminator"),
                "user_id": str(session["user_id"]),
            }
            emit("current_user_info", usr)

        self.teardown_db_session()

    def get_user_color(self, guild_id, user_id):
        member = redisqueue.get_guild_member(guild_id, user_id)
        if not member:
            return None

        guild_roles = redisqueue.get_guild(guild_id)["roles"]
        guildroles_filtered = {role["id"]: role for role in guild_roles}

        roles = []
        for r_id in member["roles"]:
            role = guildroles_filtered.get(str(r_id))
            if role:
                roles.append(role)

        color = None
        for role in [x for x in sorted(roles, key=lambda k: k["position"]) if x["color"] != 0]:
            color = f"{role['color']:02x}"
            while len(color) < 6:
                color = "0" + color

        return color

    def on_lookup_user_info(self, data):
        if "socket_guild_id" not in session:
            disconnect()
            return

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

        member = redisqueue.get_guild_member_named(guild_id, f"{name}#{discriminator}")
        if member:
            usr["id"] = str(member["id"])
            usr["username"] = member["username"]
            usr["nickname"] = member["nick"]
            usr["avatar"] = member["avatar"]
            usr["color"] = self.get_user_color(guild_id, usr["id"])
            if usr["avatar"]:
                usr[
                    "avatar_url"
                ] = f"https://cdn.discordapp.com/avatars/{usr['id']}/{usr['avatar']}.png"
            usr["roles"] = member["roles"]
            usr["discordbotsorgvoted"] = bool(
                redisqueue.redis_store.get("DiscordBotsOrgVoted/" + str(member["id"]))
            )
        else:
            member = redisqueue.get_guild_member_named(guild_id, name)
            if member:
                usr["id"] = str(member["id"])
                usr["username"] = member["username"]
                usr["nickname"] = member["nick"]
                usr["avatar"] = member["avatar"]
                usr["color"] = self.get_user_color(guild_id, usr["id"])
                if usr["avatar"]:
                    usr[
                        "avatar_url"
                    ] = f"https://cdn.discordapp.com/avatars/{usr['id']}/{usr['avatar']}.png"
                usr["roles"] = member["roles"]
                usr["discordbotsorgvoted"] = bool(
                    redisqueue.redis_store.get("DiscordBotsOrgVoted/" + str(member["id"]))
                )

        emit("lookup_user_info", usr)
        self.teardown_db_session()
