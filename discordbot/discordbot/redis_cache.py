import re
import json

from redis.asyncio import Redis

from discordbot.utils import format_message

redis_store = None


async def init_redis(url):
    global redis_store
    redis_store = await Redis.from_url(url, decode_responses=True)


async def set_scan_json(key, dict_key, dict_value_pattern):
    if not await redis_store.exists(key):
        return None, None

    for the_member in await redis_store.smembers(key):
        # the_member = await member
        if not the_member:
            continue

        parsed = json.loads(the_member)
        if re.match(str(dict_value_pattern), str(parsed[dict_key])):
            return the_member, parsed

    return None, None


async def enforce_expiring_key(key, ttl_override=None):
    if ttl_override:
        await redis_store.expire(key, ttl_override)
        return

    ttl = await redis_store.ttl(key)
    if ttl >= 0:
        new_ttl = ttl
    elif ttl == -1:
        new_ttl = 60 * 5  # 5 minutes
    else:
        new_ttl = 0

    await redis_store.expire(key, new_ttl)


async def push_message(message):
    if not message.guild:
        return

    key = f"Queue/channels/{message.channel.id}/messages"
    if not await redis_store.exists(key):
        return

    message = format_message(message)
    await redis_store.sadd(key, json.dumps(message, separators=(",", ":")))


async def delete_message(message):
    if not message.guild:
        return

    key = f"Queue/channels/{message.channel.id}/messages"
    if not await redis_store.exists(key):
        return

    unformatted_item, formatted_item = await set_scan_json(
        key, "id", message.id
    )
    if formatted_item:
        await redis_store.srem(key, unformatted_item)


async def update_message(message):
    await delete_message(message)
    await push_message(message)


async def add_member(member):
    if await redis_store.exists(f"Queue/guilds/{member.guild.id}/members"):
        await redis_store.sadd(
            f"Queue/guilds/{member.guild.id}/members",
            json.dumps({"user_id": member.id}, separators=(",", ":")),
        )


async def remove_member(member, guild=None):
    if not guild:
        guild = member.guild

    await redis_store.srem(
        f"Queue/guilds/{guild.id}/members",
        json.dumps({"user_id": member.id}, separators=(",", ":")),
    )
    await redis_store.delete(f"Queue/guilds/{guild.id}/members/{member.id}")


async def update_member(member):
    await remove_member(member)
    await add_member(member)


async def ban_member(guild, user):
    await remove_member(user, guild)


async def delete_guild(guild):
    await redis_store.delete(f"Queue/guilds/{guild.id}")


async def update_guild(guild):
    key = f"Queue/guilds/{guild.id}"

    if await redis_store.exists(key):
        await delete_guild(guild)


# Queue/channels/{channel.id}/messages"
# Queue/guilds/{guild.id}/members
# Queue/guilds/{guild.id}/members/{member.id}
# Queue/guilds/{guild.id}
