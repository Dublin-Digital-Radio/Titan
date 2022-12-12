import json
import logging
from pprint import pformat

import discord
from aiohttp import web
from config import config

from discordbot import redis_cache
from discordbot.utils import format_guild, format_message, format_user

log = logging.getLogger(__name__)


DEFAULT_CHANNEL_MESSAGES_LIMIT = 50


class Web:
    def __init__(self, bot):
        self.bot = bot  # not happy about this

        self.web_app = web.Application()
        self.web_app.add_routes(
            [
                web.get("/", self.handle_http),
                # web.get("/{name}", self.handle_http),
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
                web.get("/guilds", self.on_guilds_http),
            ]
        )

    async def start(self):
        runner = web.AppRunner(self.web_app)
        await runner.setup()

        if config["bot-http-listen-interfaces"] == "None":
            listen = None
        else:
            listen = config["bot-http-listen-interfaces"]

        log.info(
            "Starting HTTP service on %s:%s", listen, config["bot-http-port"]
        )
        site = web.TCPSite(runner, listen, config["bot-http-port"])

        await site.start()

    async def on_get_channel_messages(
        self, channel_id: int, limit=DEFAULT_CHANNEL_MESSAGES_LIMIT
    ):
        channel = self.bot.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.channel.TextChannel):
            log.error("Could not find channel %s", channel_id)
            return []

        key = f"Queue/channels/{channel_id}/messages"
        await redis_cache.redis_store.delete(key)
        me = channel.guild.get_member(self.bot.user.id)

        messages = []
        if channel.permissions_for(me).read_messages:
            log.info("reading %s messages for channel %s", limit, channel_id)
            async for message in channel.history(limit=limit):
                messages.append(format_message(message))
            log.info("Read messages from channel %s", channel_id)
        else:
            log.error(
                "Do not have permission to read messages from channel %s",
                channel.id,
            )

        log.info("Adding messages for channel to redis")
        await redis_cache.redis_store.sadd(
            key,
            "",
            *[json.dumps(m, separators=(",", ":")) for m in messages],
        )
        log.info("Done messages for channel to redis")

        return messages

    async def on_get_guild_member(self, guild, user_id: int):
        key = f"Queue/guilds/{guild.id}/members/{user_id}"

        if not (member := guild.get_member(user_id)):
            members = await guild.query_members(user_ids=[user_id], cache=True)

            if not len(members):
                await redis_cache.redis_store.set(key, "")
                await redis_cache.enforce_expiring_key(key, 15)
                return {}

            member = members[0]

        await redis_cache.redis_store.set(
            key, json.dumps(format_user(member), separators=(",", ":"))
        )
        await redis_cache.enforce_expiring_key(key)

        return format_user(member)

    async def on_get_guild_member_named(self, guild_id: int, query):
        if not (guild := self.bot.get_guild(guild_id)):
            return {}

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
            await self.on_get_guild_member(guild, members.id)

        key = f"Queue/custom/guilds/{guild_id}/member_named/{query}"
        await redis_cache.redis_store.set(key, result)
        await redis_cache.enforce_expiring_key(key)

        return result

    async def on_list_guild_members(self, guild_id: int):
        if not (guild := self.bot.get_guild(guild_id)):
            return

        member_ids = []
        for member in guild.members:
            member_ids.append(
                json.dumps({"user_id": member.id}, separators=(",", ":"))
            )
            await self.on_get_guild_member(guild, member.id)

        key = f"Queue/guilds/{guild_id}/members"
        await redis_cache.redis_store.sadd(key, *member_ids)

        return member_ids

    async def on_get_guild(self, guild_id: int):
        log.info("looking up guild %s", guild_id)
        if not (guild := self.bot.get_guild(guild_id)):
            log.info("no guild found")
            return {}

        if guild.me and guild.me.guild_permissions.manage_webhooks:
            try:
                server_webhooks = await guild.webhooks()
            except:
                log.exception("Could not get guild webhooks")
                server_webhooks = []
        else:
            server_webhooks = []

        key = f"Queue/guilds/{guild_id}"
        await redis_cache.redis_store.set(
            key,
            json.dumps(
                format_guild(guild, server_webhooks), separators=(",", ":")
            ),
        )
        await redis_cache.enforce_expiring_key(key)

        return format_guild(guild, server_webhooks)

    async def on_get_guilds(self):
        log.info("on get guilds")
        return self.bot.guilds

    async def on_get_user(self, user_id: int):
        if not (user := self.bot.get_user(user_id)):
            return {}

        user_formatted = {
            "id": user.id,
            "username": user.name,
            "discriminator": user.discriminator,
            "avatar": user.avatar.key if user.avatar else None,
            "bot": user.bot,
        }

        key = f"Queue/users/{user_id}"
        await redis_cache.redis_store.set(
            key, json.dumps(user_formatted, separators=(",", ":"))
        )
        await redis_cache.enforce_expiring_key(key)

        return user_formatted

    async def handle_http(self, request):
        log.info("handle_http")
        name = request.match_info.get("name", "Anonymous")
        text = "Hello, " + name
        return web.Response(text=text)

    async def on_get_channel_messages_http(self, request):
        log.info("on_get_channel_messages_http")
        channel_id = request.match_info.get("channel_id")
        messages = await self.on_get_channel_messages(
            int(channel_id),
            int(
                request.match_info.get("limit", DEFAULT_CHANNEL_MESSAGES_LIMIT)
            ),
        )
        log.info("on_get_channel_messages_http returning %s", len(messages))
        return web.json_response(messages)

    async def on_get_guild_member_http(self, request):
        log.info("on_get_guild_member_http")

        guild_id = request.match_info.get("guild_id")
        user_id = request.match_info.get("user_id")

        if not (guild := self.bot.get_guild(int(guild_id))):
            return {}

        result = await self.on_get_guild_member(guild, int(user_id))
        log.info("on_get_guild_member_http returning\n%s", pformat(result))

        return web.json_response(result)

    async def on_get_guild_member_named_http(self, request):
        log.info("on_get_guild_member_named_http")
        guild_id = request.match_info.get("guild_id")
        query = request.match_info.get("query")
        result = await self.on_get_guild_member_named(int(guild_id), query)

        log.info(
            "on_get_guild_member_named_http returning\n%s", pformat(result)
        )
        return web.json_response(result)

    async def on_list_guild_members_http(self, request):
        log.info("on_list_guild_members_http")
        guild_id = request.match_info.get("guild_id")
        member_ids = await self.on_list_guild_members(int(guild_id))
        log.info(
            "on_list_guild_members_http returning\n%s", pformat(member_ids)
        )
        return web.json_response(member_ids)

    async def on_get_guild_http(self, request):
        log.info("on_get_guild_http")
        guild_id = request.match_info.get("guild_id")
        guild = await self.on_get_guild(int(guild_id))
        log.info("on_get_guild_http returning\n%s", pformat(guild))
        return web.json_response(guild)

    async def on_get_user_http(self, request):
        log.info("on_get_user_http")
        user_id = request.match_info.get("user_id")
        user_formatted = await self.on_get_user(int(user_id))
        log.info("on_get_user_http returning\n%s", pformat(user_formatted))
        return web.json_response(user_formatted)

    async def on_guilds_http(self, request):
        guilds = await self.on_get_guilds()
        return web.json_response([repr(x) for x in guilds])
