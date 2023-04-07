import json
import logging
from pprint import pformat

import discord
from quart import Quart, jsonify, request

from discordbot import redis_cache
from discordbot.utils import format_guild, format_message, format_user, guild_webhooks

log = logging.getLogger(__name__)

DEFAULT_CHANNEL_MESSAGES_LIMIT = 50

bot = None
web_app = Quart(__name__)


@web_app.route("/<name>")
async def handle_http(name):
    log.info("handle_http")
    return "Hello, " + name


@web_app.get("/channel_messages/<channel_id>")
async def on_get_channel_messages_http(channel_id):
    log.info("on_get_channel_messages_http")

    channel = bot.get_channel(int(channel_id))
    if not channel or not isinstance(channel, discord.channel.TextChannel):
        log.error("Could not find channel %s", channel_id)
        return jsonify([])

    limit = int(request.args.get("limit", DEFAULT_CHANNEL_MESSAGES_LIMIT))

    await redis_cache.delete_messages(channel)

    me = channel.guild.get_member(bot.user.id)
    if not channel.permissions_for(me).read_messages:
        log.error(
            "Do not have permission to read messages from channel %s",
            channel.id,
        )
        return []

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
    return messages


@web_app.get("/guild/<guild_id>/member/<user_id>")
async def on_get_guild_member_http(guild_id, user_id):
    log.info("on_get_guild_member_http")

    if not (guild := bot.get_guild(int(guild_id))):
        return {}

    if not (member := guild.get_member(int(user_id))):
        members = await guild.query_members(user_ids=[user_id], cache=True)

        if not len(members):
            await redis_cache.remove_member_from_guild(guild, user_id)
            return {}
        member = members[0]

    await redis_cache.add_member_to_guild(guild, member)
    result = format_user(member)
    log.debug("on_get_guild_member_http returning\n%s", pformat(result))

    return result


# TODO - this looks broken
@web_app.get("/guild/<guild_id>/member-name/<query>")
async def on_get_guild_member_named_http(guild_id, query):
    log.info("on_get_guild_member_named_http : '%s'", query)

    if not (guild := bot.get_guild(int(guild_id))):
        log.error("guild not found")
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
        member_id = {}
    else:
        member_id = json.dumps({"user_id": members.id}, separators=(",", ":"))
        await redis_cache.add_member_to_guild(guild, members)

    await redis_cache.add_named_member_to_guild(guild, query, member_id or "")

    log.debug(
        "on_get_guild_member_named_http returning\n%s", pformat(member_id)
    )
    return member_id


@web_app.get("/guild/<guild_id>/members")
async def on_list_guild_members_http(guild_id):
    log.info("on_list_guild_members_http")

    if not (guild := bot.get_guild(int(guild_id))):
        return jsonify([])

    member_ids = []
    for member in guild.members:
        member_ids.append(
            json.dumps({"user_id": member.id}, separators=(",", ":"))
        )
        await redis_cache.add_member_to_guild(guild, member)

    await redis_cache.add_members(guild.id, member_ids)
    log.debug("on_list_guild_members_http returning\n%s", pformat(member_ids))
    return jsonify(member_ids)


@web_app.get("/guild/<guild_id>")
async def on_get_guild_http(guild_id):
    log.info("on_get_guild_http")

    if not (guild := bot.get_guild(int(guild_id))):
        log.info("no guild found")
        return {}
    server_webhooks = await guild_webhooks(guild)

    await redis_cache.update_guild(guild, server_webhooks=server_webhooks)

    log.debug("on_get_guild_http returning\n%s", pformat(guild))
    return format_guild(guild, server_webhooks)


@web_app.get("/user/<user_id>")
async def on_get_user_http(user_id):
    log.info("on_get_user_http")
    if not (user := bot.get_user(int(user_id))):
        return {}

    user_formatted = {
        "id": user.id,
        "username": user.name,
        "discriminator": user.discriminator,
        "avatar": user.avatar.key if user.avatar else None,
        "bot": user.bot,
    }

    await redis_cache.add_user(user.id, user_formatted)

    log.debug("on_get_user_http returning\n%s", pformat(user_formatted))
    return user_formatted


@web_app.get("/guilds")
async def on_guilds_http():
    return jsonify([repr(x) for x in bot.guilds])


def web_init(bot_obj):
    log.info("web init")

    global bot
    bot = bot_obj
