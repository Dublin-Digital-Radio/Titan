import re
import json
import logging

import discord
from aiohttp import web

from discordbot.utils import format_guild, format_message, format_user

log = logging.getLogger(__name__)


DEFAULT_CHANNEL_MESSAGES_LIMIT = 50


class Web(discord.AutoShardedClient):
    def __init__(self):
        self.web_app = web.Application()
        self.running_tasks = set()

    def init_web(self):
        self.running_tasks = set()

        self.web_app = web.Application()
        self.web_app.add_routes(
            [
                web.get("/", self.handle),
                web.get("/{name}", self.handle),
                web.get(
                    "/channel_messages/{channel_id}",
                    self.on_get_channel_messages,
                ),
                web.get(
                    "/guild/{guild_id}/member/{user_id}",
                    self.on_get_guild_member,
                ),
                web.get(
                    "/guild/{guild_id}/member-name/{query}",
                    self.on_get_guild_member_named,
                ),
                web.get("/guild/members/", self.on_list_guild_members),
                web.get("/guild/{guild_id}", self.on_get_guild),
                web.get("/user/{user_id}", self.on_get_user),
            ]
        )

        web.run_app(self.web_app)

    async def set_scan_json(self, key, dict_key, dict_value_pattern):
        if not await self.connection.exists(key):
            return None, None

        for the_member in await self.connection.smembers(key):
            # the_member = await member
            if not the_member:
                continue

            parsed = json.loads(the_member)
            if re.match(str(dict_value_pattern), str(parsed[dict_key])):
                return the_member, parsed

        return None, None

    async def enforce_expiring_key(self, key, ttl_override=None):
        if ttl_override:
            await self.connection.expire(key, ttl_override)
            return

        ttl = await self.connection.ttl(key)
        if ttl >= 0:
            new_ttl = ttl
        elif ttl == -1:
            new_ttl = 60 * 5  # 5 minutes
        else:
            new_ttl = 0

        await self.connection.expire(key, new_ttl)

    async def handle(self, request):
        name = request.match_info.get("name", "Anonymous")
        text = "Hello, " + name
        return web.Response(text=text)

    async def on_get_channel_messages(self, request):
        channel_id = request.match_info.get("channel_id")
        channel = self.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.channel.TextChannel):
            log.error("Could not find channel %s", channel_id)
            return

        me = channel.guild.get_member(self.user.id)

        messages = []
        if channel.permissions_for(me).read_messages:
            limit = request.match_info.get(
                "limit", DEFAULT_CHANNEL_MESSAGES_LIMIT
            )
            log.info("reading %s messages for channel %s", limit, channel_id)
            async for message in channel.history(limit=limit):
                messages.append(
                    json.dumps(format_message(message), separators=(",", ":"))
                )
            log.info("Read messages from channel %s", channel_id)
        else:
            log.error(
                "Do not have permission to read messages from channel %s",
                channel.id,
            )

        log.info("Adding messages for channel to redis")
        return web.json_response(messages)

    async def push_message(self, message):
        if not message.guild:
            return

        key = f"Queue/channels/{message.channel.id}/messages"
        if not await self.connection.exists(key):
            return

        message = format_message(message)
        await self.connection.sadd(
            key, json.dumps(message, separators=(",", ":"))
        )

    async def delete_message(self, message):
        if not message.guild:
            return

        key = f"Queue/channels/{message.channel.id}/messages"
        if not await self.connection.exists(key):
            return

        unformatted_item, formatted_item = await self.set_scan_json(
            key, "id", message.id
        )
        if formatted_item:
            await self.connection.srem(key, unformatted_item)

    async def update_message(self, message):
        await self.delete_message(message)
        await self.push_message(message)

    async def on_get_guild_member(self, request):
        guild_id = request.match_info.get("guild_id")
        if not (guild := self.get_guild(guild_id)):
            return

        user_id = request.match_info.get("user_id")
        if not (member := guild.get_member(user_id)):
            members = await guild.query_members(user_ids=[user_id], cache=True)

            if not len(members):
                return web.json_response({})

            member = members[0]

        return web.json_response(format_user(member))

    async def on_get_guild_member_named(self, request):
        guild_id = request.match_info.get("guild_id")

        if not (guild := self.get_guild(guild_id)):
            return

        query = request.match_info.get("query")
        members = None
        if guild.members and len(query) > 5 and query[-5] == "#":
            potential_discriminator = query[-4:]
            members = discord.utils.get(
                guild.members,
                name=query[:-5],
                discriminator=potential_discriminator,
            )
            if not members:
                members = discord.utils.get(
                    guild.members,
                    nick=query[:-5],
                    discriminator=potential_discriminator,
                )

        if not members:
            result = ""
        else:
            result = json.dumps(
                {"user_id": (members.id)}, separators=(",", ":")
            )
            get_guild_member_key = (
                f"Queue/guilds/{guild.id}/members/{members.id}"
            )
            get_guild_member_param = {
                "guild_id": guild.id,
                "user_id": members.id,
            }
            await self.on_get_guild_member(
                get_guild_member_key, get_guild_member_param
            )

        return web.json_response(result)

    async def on_list_guild_members(self, request):
        guild_id = request.match_info.get("guild_id")
        if not (guild := self.get_guild(guild_id)):
            return

        member_ids = []
        for member in guild.members:
            member_ids.append(
                json.dumps({"user_id": member.id}, separators=(",", ":"))
            )
            get_guild_member_key = (
                f"Queue/guilds/{guild.id}/members/{member.id}"
            )
            get_guild_member_param = {
                "guild_id": guild.id,
                "user_id": member.id,
            }
            await self.on_get_guild_member(
                get_guild_member_key, get_guild_member_param
            )

        return web.json_response(member_ids)

    async def add_member(self, member):
        if await self.connection.exists(
            f"Queue/guilds/{member.guild.id}/members"
        ):
            await self.connection.sadd(
                f"Queue/guilds/{member.guild.id}/members",
                json.dumps({"user_id": member.id}, separators=(",", ":")),
            )

        get_guild_member_key = (
            f"Queue/guilds/{member.guild.id}/members/{member.id}"
        )
        get_guild_member_param = {
            "guild_id": member.guild.id,
            "user_id": member.id,
        }
        await self.on_get_guild_member(
            get_guild_member_key, get_guild_member_param
        )

    async def remove_member(self, member, guild=None):
        if not guild:
            guild = member.guild

        await self.connection.srem(
            f"Queue/guilds/{guild.id}/members",
            json.dumps({"user_id": member.id}, separators=(",", ":")),
        )
        await self.connection.delete(
            f"Queue/guilds/{guild.id}/members/{member.id}"
        )

    async def update_member(self, member):
        await self.remove_member(member)
        await self.add_member(member)

    async def ban_member(self, guild, user):
        await self.remove_member(user, guild)

    async def on_get_guild(self, request):
        guild_id = request.match_info.get("guild_id")
        if not (guild := self.get_guild(guild_id)):
            return

        if guild.me and guild.me.guild_permissions.manage_webhooks:
            try:
                server_webhooks = await guild.webhooks()
            except:
                log.exception("Could not get guild webhooks")
                server_webhooks = []
        else:
            server_webhooks = []

        return web.json_response(format_guild(guild, server_webhooks))

    async def delete_guild(self, guild):
        await self.connection.delete(f"Queue/guilds/{guild.id}")

    async def update_guild(self, guild):
        key = f"Queue/guilds/{guild.id}"

        if await self.connection.exists(key):
            await self.delete_guild(guild)
            await self.on_get_guild(key, {"guild_id": guild.id})
        await self.enforce_expiring_key(key)

    async def on_get_user(self, request):
        user_id = request.match_info.get("user_id")
        if not (user := self.get_user(user_id)):
            return

        user_formatted = {
            "id": user.id,
            "username": user.name,
            "discriminator": user.discriminator,
            "avatar": user.avatar.key if user.avatar else None,
            "bot": user.bot,
        }
        return web.json_response(user_formatted)
