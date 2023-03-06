from aiohttp import web
import json
import logging

from .bot import Titan
from discordbot.utils import format_guild, format_message, format_user
import discord

log = logging.getLogger(__name__)

DEFAULT_CHANNEL_MESSAGES_LIMIT = 50


class HTTPBot(Titan):
    def __init__(self):
        self.web_app = web.Application()
        self.running_tasks = set()

    def init_web(self):
        self.running_tasks = set()

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
                web.get("/guild/members/", self.on_list_guild_members_http),
                web.get("/guild/{guild_id}", self.on_get_guild_http),
                web.get("/user/{user_id}", self.on_get_user_http),
            ]
        )

        web.run_app(self.web_app)

    async def handle_http(self, request):
        name = request.match_info.get("name", "Anonymous")
        text = "Hello, " + name
        return web.Response(text=text)

    async def on_get_channel_messages_http(self, request):
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

    async def on_get_guild_member_http(self, request):
        guild_id = request.match_info.get("guild_id")
        user_id = request.match_info.get("user_id")
        return self.on_get_guild_member(guild_id, user_id)

    async def on_get_guild_member_named_http(self, request):
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

    async def on_list_guild_members_http(self, request):
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

    async def on_get_guild_http(self, request):
        guild_id = request.match_info.get("guild_id")
        return self.on_get_guild(guild_id)

    async def on_get_user_http(self, request):
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
