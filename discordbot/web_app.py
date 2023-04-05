import json
import logging
from pprint import pformat

import discord
from aiohttp import web
from config import config

from discordbot import redis_cache
from discordbot.utils import format_guild, format_message, format_user, guild_webhooks

log = logging.getLogger(__name__)

DEFAULT_CHANNEL_MESSAGES_LIMIT = 50

bot = None


async def handle_http(self, request):
    log.info("handle_http")
    name = request.match_info.get("name", "Anonymous")
    text = "Hello, " + name
    return web.Response(text=text)


async def on_get_channel_messages_http(request):
    log.info("on_get_channel_messages_http")

    channel_id = request.match_info.get("channel_id")
    channel = bot.get_channel(int(channel_id))
    if not channel or not isinstance(channel, discord.channel.TextChannel):
        log.error("Could not find channel %s", channel_id)
        return web.json_response([])

    limit = int(request.match_info.get("limit", DEFAULT_CHANNEL_MESSAGES_LIMIT))

    await redis_cache.delete_messages(channel)
    me = channel.guild.get_member(bot.user.id)

    if not channel.permissions_for(me).read_messages:
        log.error(
            "Do not have permission to read messages from channel %s",
            channel.id,
        )
        return web.json_response([])

    log.info("reading %s messages for channel %s", limit, channel.id)
    messages = [
        format_message(message)
        async for message in channel.history(limit=limit)
    ]
    log.info("Read messages from channel %s", channel.id)

    log.info("Adding messages for channel to redis")
    await redis_cache.add_messages(channel, messages)
    log.info("Done messages for channel to redis")

    log.debug("on_get_channel_messages_http returning %s", len(messages))
    return web.json_response(messages)


async def on_get_guild_member_http(request):
    log.info("on_get_guild_member_http")

    guild_id = request.match_info.get("guild_id")
    user_id = request.match_info.get("user_id")

    if not (guild := bot.get_guild(int(guild_id))):
        return {}

    if not (member := guild.get_member(int(user_id))):
        members = await guild.query_members(user_ids=[user_id], cache=True)

        if not len(members):
            await redis_cache.remove_member_from_guild(guild, user_id)
            return web.json_response({})
        member = members[0]

    await redis_cache.add_member_to_guild(guild, member)
    result = format_user(member)
    log.debug("on_get_guild_member_http returning\n%s", pformat(result))

    return web.json_response(result)


async def on_get_guild_member_named_http(request):
    log.info("on_get_guild_member_named_http")
    guild_id = request.match_info.get("guild_id")
    query = request.match_info.get("query")

    if not (guild := bot.get_guild(int(guild_id))):
        return web.json_response({})

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
        member_id = ""
    else:
        member_id = json.dumps({"user_id": members.id}, separators=(",", ":"))
        await redis_cache.add_member_to_guild(guild, members)

    await redis_cache.add_named_member_to_guild(guild, query, member_id)

    log.debug(
        "on_get_guild_member_named_http returning\n%s", pformat(member_id)
    )
    return web.json_response(member_id)


async def on_list_guild_members_http(request):
    log.info("on_list_guild_members_http")
    guild_id = request.match_info.get("guild_id")
    if not (guild := bot.get_guild(int(guild_id))):
        return web.json_response([])

    member_ids = []
    for member in guild.members:
        member_ids.append(
            json.dumps({"user_id": member.id}, separators=(",", ":"))
        )
        await redis_cache.add_member_to_guild(guild, member)

    await redis_cache.add_members(guild.id, member_ids)
    log.debug("on_list_guild_members_http returning\n%s", pformat(member_ids))
    return web.json_response(member_ids)


async def on_get_guild_http(request):
    log.info("on_get_guild_http")
    guild_id = request.match_info.get("guild_id")

    if not (guild := bot.get_guild(int(guild_id))):
        log.info("no guild found")
        return web.json_response({})
    server_webhooks = await guild_webhooks(guild)

    await redis_cache.update_guild(guild, server_webhooks=server_webhooks)

    log.debug("on_get_guild_http returning\n%s", pformat(guild))
    return web.json_response(format_guild(guild, server_webhooks))


async def on_get_user_http(request):
    log.info("on_get_user_http")
    user_id = request.match_info.get("user_id")
    if not (user := bot.get_user(int(user_id))):
        return web.json_response({})

    user_formatted = {
        "id": user.id,
        "username": user.name,
        "discriminator": user.discriminator,
        "avatar": user.avatar.key if user.avatar else None,
        "bot": user.bot,
    }

    await redis_cache.add_user(user.id, user_formatted)

    log.debug("on_get_user_http returning\n%s", pformat(user_formatted))
    return web.json_response(user_formatted)


async def on_guilds_http(request):
    return web.json_response([repr(x) for x in bot.guilds])


web_app = web.Application()
web_app.add_routes(
    [
        web.get("/", handle_http),
        # web.get("/{name}", handle_http),
        web.get(
            "/channel_messages/{channel_id}",
            on_get_channel_messages_http,
        ),
        web.get(
            "/guild/{guild_id}/member/{user_id}",
            on_get_guild_member_http,
        ),
        web.get(
            "/guild/{guild_id}/member-name/{query}",
            on_get_guild_member_named_http,
        ),
        web.get(
            "/guild/{guild_id}/members/",
            on_list_guild_members_http,
        ),
        web.get("/guild/{guild_id}", on_get_guild_http),
        web.get("/user/{user_id}", on_get_user_http),
        web.get("/guilds", on_guilds_http),
    ]
)


async def web_start(bot_obj):
    global bot
    bot = bot_obj

    runner = web.AppRunner(web_app)
    await runner.setup()

    if config["bot-http-listen-interfaces"] == "None":
        listen = None
    else:
        listen = config["bot-http-listen-interfaces"]

    log.info("Starting HTTP service on %s:%s", listen, config["bot-http-port"])
    site = web.TCPSite(runner, listen, config["bot-http-port"])

    await site.start()
