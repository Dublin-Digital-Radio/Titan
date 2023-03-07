import re
import json

from redis.asyncio import Redis

from discordbot.utils import format_message

connection = await Redis.from_url("redis://")


async def init_redis(url):
    global connection
    connection = await Redis.from_url(url, decode_responses=True)


async def set_scan_json(key, dict_key, dict_value_pattern):
    if not await connection.exists(key):
        return None, None

    for the_member in await connection.smembers(key):
        # the_member = await member
        if not the_member:
            continue

        parsed = json.loads(the_member)
        if re.match(str(dict_value_pattern), str(parsed[dict_key])):
            return the_member, parsed

    return None, None


async def push_message(message):
    if not message.guild:
        return

    key = f"Queue/channels/{message.channel.id}/messages"
    if not await connection.exists(key):
        return

    message = format_message(message)
    await connection.sadd(key, json.dumps(message, separators=(",", ":")))


async def delete_message(message):
    if not message.guild:
        return

    key = f"Queue/channels/{message.channel.id}/messages"
    if not await connection.exists(key):
        return

    unformatted_item, formatted_item = await set_scan_json(
        key, "id", message.id
    )
    if formatted_item:
        await connection.srem(key, unformatted_item)


async def update_message(message):
    await delete_message(message)
    await push_message(message)


async def add_member(member):
    if await connection.exists(f"Queue/guilds/{member.guild.id}/members"):
        await connection.sadd(
            f"Queue/guilds/{member.guild.id}/members",
            json.dumps({"user_id": member.id}, separators=(",", ":")),
        )


async def remove_member(member, guild=None):
    if not guild:
        guild = member.guild

    await connection.srem(
        f"Queue/guilds/{guild.id}/members",
        json.dumps({"user_id": member.id}, separators=(",", ":")),
    )
    await connection.delete(f"Queue/guilds/{guild.id}/members/{member.id}")


async def update_member(member):
    await remove_member(member)
    await add_member(member)


async def ban_member(guild, user):
    await remove_member(user, guild)


async def delete_guild(guild):
    await connection.delete(f"Queue/guilds/{guild.id}")


async def update_guild(guild):
    key = f"Queue/guilds/{guild.id}"

    if await connection.exists(key):
        await delete_guild(guild)


# Queue/channels/{channel.id}/messages"
# Queue/guilds/{guild.id}/members
# Queue/guilds/{guild.id}/members/{member.id}
# Queue/guilds/{guild.id}
