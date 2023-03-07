import json
import logging

import discord
from aiohttp import web

from discordbot import redis_cache
from discordbot.utils import format_guild, format_message, format_user

log = logging.getLogger(__name__)


DEFAULT_CHANNEL_MESSAGES_LIMIT = 50


class Web:
    def __init__(self, bot):
        self.bot = bot

        self.web_app = web.Application()
        self.web_app.add_routes(
            [
                web.get("/", self.handle_http),
                web.get("/{name}", self.handle_http),
                web.get(
                    "/channel_messages/{channel_id}",
                    self.on_get_channel_messages_http,
                ),
                web.get(
                    "/guild/{guild_id}/member/{user_id}",
                    self.on_get_guild_member_http,
                ),
                web.get(
                    "/guild/{guild_id}/member-name/{query}",
                    self.on_get_guild_member_named_http,
                ),
                web.get(
                    "/guild/{guild_id}/members/",
                    self.on_list_guild_members_http,
                ),
                web.get("/guild/{guild_id}", self.on_get_guild_http),
                web.get("/user/{user_id}", self.on_get_user_http),
            ]
        )

        web.run_app(self.web_app)

    async def on_get_channel_messages(
        self, channel_id, limit=DEFAULT_CHANNEL_MESSAGES_LIMIT
    ):
        key = (f"Queue/channels/{channel_id}/messages",)
        channel = self.bot.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.channel.TextChannel):
            log.error("Could not find channel %s", channel_id)
            return

        await redis_cache.connection.delete(key)
        me = channel.guild.get_member(self.bot.user.id)

        messages = []
        if channel.permissions_for(me).read_messages:
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
        await redis_cache.connection.sadd(key, "", *messages)
        log.info("Done messages for channel to redis")

        return messages

    async def on_get_guild_member(self, guild_id, user_id):
        key = f"Queue/guilds/{guild_id}/members/{user_id}"

        if not (guild := self.bot.get_guild(guild_id)):
            return

        if not (member := guild.get_member(user_id)):
            members = await guild.query_members(user_ids=[user_id], cache=True)

            if not len(members):
                await redis_cache.connection.set(key, "")
                await redis_cache.enforce_expiring_key(key, 15)
                return {}

            member = members[0]

        await redis_cache.connection.set(
            key, json.dumps(format_user(member), separators=(",", ":"))
        )
        await redis_cache.enforce_expiring_key(key)

        return format_user(member)

    async def on_get_guild_member_named(self, guild_id, query):
        key = f"Queue/custom/guilds/{guild_id}/member_named/{query}"

        if not (guild := self.bot.get_guild(guild_id)):
            return

        members = None
        if guild.members and len(query) > 5 and query[-5] == "#":
            potential_discriminator = query[-4:]
            members = await discord.utils.get(
                guild.members,
                name=query[:-5],
                discriminator=potential_discriminator,
            )
            if not members:
                members = await discord.utils.get(
                    guild.members,
                    nick=query[:-5],
                    discriminator=potential_discriminator,
                )

        if not members:
            result = ""
        else:
            result = json.dumps({"user_id": members.id}, separators=(",", ":"))
            get_guild_member_key = (
                f"Queue/guilds/{guild.id}/members/{members.id}"
            )
            get_guild_member_param = {
                "guild_id": guild.id,
                "user_id": members.id,
            }
            # TODO
            await self.on_get_guild_member(
                get_guild_member_key, get_guild_member_param
            )

        await redis_cache.connection.set(key, result)
        await redis_cache.enforce_expiring_key(key)

        return result

    async def on_list_guild_members(self, guild_id):
        key = f"Queue/guilds/{guild_id}/members"

        if not (guild := self.bot.get_guild(guild_id)):
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
            # TODO
            await self.on_get_guild_member(
                get_guild_member_key, get_guild_member_param
            )

        await redis_cache.connection.sadd(key, *member_ids)

        return member_ids

    async def on_get_guild(self, guild_id):
        key = f"Queue/guilds/{guild_id}"

        if not (guild := self.bot.get_guild(guild_id)):
            return

        if guild.me and guild.me.guild_permissions.manage_webhooks:
            try:
                server_webhooks = await guild.webhooks()
            except:
                log.exception("Could not get guild webhooks")
                server_webhooks = []
        else:
            server_webhooks = []

        await redis_cache.connection.set(
            key,
            json.dumps(
                format_guild(guild, server_webhooks), separators=(",", ":")
            ),
        )
        await redis_cache.enforce_expiring_key(key)

        return format_guild(guild, server_webhooks)

    async def on_get_user(self, user_id):
        key = f"Queue/users/{user_id}"

        if not (user := self.bot.get_user(user_id)):
            return

        user_formatted = {
            "id": user.id,
            "username": user.name,
            "discriminator": user.discriminator,
            "avatar": user.avatar.key if user.avatar else None,
            "bot": user.bot,
        }

        await redis_cache.connection.set(
            key, json.dumps(user_formatted, separators=(",", ":"))
        )
        await redis_cache.enforce_expiring_key(key)

        return user_formatted

    async def handle_http(self, request):
        name = request.match_info.get("name", "Anonymous")
        text = "Hello, " + name
        return web.Response(text=text)

    async def on_get_channel_messages_http(self, request):
        channel_id = request.match_info.get("channel_id")
        messages = self.on_get_channel_messages(
            channel_id,
            request.match_info.get("limit", DEFAULT_CHANNEL_MESSAGES_LIMIT),
        )
        return web.json_response(messages)

    async def on_get_guild_member_http(self, request):
        guild_id = request.match_info.get("guild_id")
        user_id = request.match_info.get("user_id")
        result = self.on_get_guild_member(guild_id, user_id)
        return web.json_response(result)

    async def on_get_guild_member_named_http(self, request):
        guild_id = request.match_info.get("guild_id")
        query = request.match_info.get("query")
        result = self.on_get_guild_member_named(guild_id, query)

        return web.json_response(result)

    async def on_list_guild_members_http(self, request):
        guild_id = request.match_info.get("guild_id")
        member_ids = self.on_list_guild_members(guild_id)
        return web.json_response(member_ids)

    async def on_get_guild_http(self, request):
        guild_id = request.match_info.get("guild_id")
        guild = self.on_get_guild(guild_id)
        return web.json_response(guild)

    async def on_get_user_http(self, request):
        user_id = request.match_info.get("user_id")
        user_formatted = self.on_get_user(user_id)
        return web.json_response(user_formatted)
