import re
import json
import logging
from functools import wraps

from redis.asyncio import Redis
from redis.exceptions import ConnectionError

from discordbot.utils import format_guild, format_message, format_user

log = logging.getLogger(__name__)

redis_store = None


def retry(func):
    @wraps(func)
    async def retry_func(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ConnectionError:
            log.error("Redis connection error - retrying")
            await redis_store.connect()
            return await func(*args, **kwargs)

    return retry_func


async def init_redis(url):
    global redis_store
    redis_store = await Redis.from_url(url, decode_responses=True)


@retry
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


@retry
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


@retry
async def push_message(message):
    if not message.guild:
        return

    key = f"Queue/channels/{message.channel.id}/messages"
    if not await redis_store.exists(key):
        return

    message = format_message(message)
    await redis_store.sadd(key, json.dumps(message, separators=(",", ":")))


@retry
async def add_messages(channel, messages):
    key = f"Queue/channels/{channel.id}/messages"
    await redis_store.sadd(
        key,
        "",
        *[json.dumps(m, separators=(",", ":")) for m in messages],
    )


@retry
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


@retry
async def delete_messages(channel):
    key = f"Queue/channels/{channel.id}/messages"
    await redis_store.delete(key)


@retry
async def update_message(message):
    await delete_message(message)
    await push_message(message)


@retry
async def add_members(guild_id, member_ids):
    key = f"Queue/guilds/{guild_id}/members"
    await redis_store.sadd(key, *member_ids)


@retry
async def add_member(member):
    if await redis_store.exists(f"Queue/guilds/{member.guild.id}/members"):
        await redis_store.sadd(
            f"Queue/guilds/{member.guild.id}/members",
            json.dumps({"user_id": member.id}, separators=(",", ":")),
        )


@retry
async def remove_member(member, guild=None):
    if not guild:
        guild = member.guild

    await redis_store.srem(
        f"Queue/guilds/{guild.id}/members",
        json.dumps({"user_id": member.id}, separators=(",", ":")),
    )
    await redis_store.delete(f"Queue/guilds/{guild.id}/members/{member.id}")


@retry
async def add_member_to_guild(guild, member):
    key = f"Queue/guilds/{guild.id}/members/{member.id}"
    await redis_store.set(
        key, json.dumps(format_user(member), separators=(",", ":"))
    )
    await enforce_expiring_key(key)


@retry
async def remove_member_from_guild(guild, user_id):
    key = f"Queue/guilds/{guild.id}/members/{user_id}"
    await redis_store.set(key, "")
    await enforce_expiring_key(key, 15)


@retry
async def update_member(member):
    await remove_member(member)
    await add_member(member)


@retry
async def ban_member(guild, user):
    await remove_member(user, guild)


@retry
async def add_named_member_to_guild(guild, query, member_id):
    key = f"Queue/custom/guilds/{guild.id}/member_named/{query}"
    await redis_store.set(key, member_id)
    await enforce_expiring_key(key)


@retry
async def delete_guild(guild):
    await redis_store.delete(f"Queue/guilds/{guild.id}")


@retry
async def update_guild(guild, server_webhooks=None):
    key = f"Queue/guilds/{guild.id}"

    if await redis_store.exists(key):
        await delete_guild(guild)

    await redis_store.set(
        key,
        json.dumps(format_guild(guild, server_webhooks), separators=(",", ":")),
    )

    await enforce_expiring_key(key)


# Queue/channels/{channel.id}/messages"
# Queue/guilds/{guild.id}/members
# Queue/guilds/{guild.id}/members/{member.id}
# Queue/guilds/{guild.id}


@retry
async def add_user(user_id, user_formatted):
    key = f"Queue/users/{user_id}"

    await redis_store.set(
        key, json.dumps(user_formatted, separators=(",", ":"))
    )
    await enforce_expiring_key(key)
