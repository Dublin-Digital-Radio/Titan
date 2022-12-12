import json
import time
import logging

import redis
from titanembeds.formatters import format_guild, format_message, format_user

log = logging.getLogger(__name__)

redis_store = redis.Redis()
redis_url = ""


def init_redis(url):
    global redis_store
    global redis_url
    redis_store = redis.Redis.from_url(url, decode_responses=True)
    redis_url = url


def get(key, resource, params, *, data_type="str"):
    key = "Queue" + key
    _get = redis_store.smembers if data_type == "set" else redis_store.get

    try:
        data = _get(key)
    except redis.exceptions.ConnectionError:
        log.error("lost redis connection - retrying")
        if redis_url:
            init_redis(redis_url)
        else:
            log.error("no redis url")
            raise
        data = _get(key)

    loop_count = 0
    while (not data and data != "") and loop_count < 50:
        if loop_count % 25 == 0:
            redis_store.publish(
                "discord-api-req",
                json.dumps(
                    {"key": key, "resource": resource, "params": params}
                ),
            )
        time.sleep(0.1)
        data = _get(key)
        loop_count += 1
    redis_store.expire(key, 60 * 5)

    if not data:
        return None

    if data_type == "set":
        return [json.loads(d) for d in list(data) if d != ""]

    return json.loads(data)


def validate_not_none(key, data_key, data):
    if data[data_key] is None:
        redis_store.delete(key)
        time.sleep(0.5)
        return False
    return True


def get_channel_messages(guild_id, channel_id, after_snowflake=0):
    log.info("get_channel_messages")
    key = f"/channels/{channel_id}/messages"

    channel_messages = redis_store.smembers("Queue" + key)
    if not channel_messages:
        channel_messages = on_get_channel_messages(key, channel_id)
    if not channel_messages:
        log.warning("Got none from channel messages")
        return []
    log.info("get_channel_messages : got %s messages", len(channel_messages))

    msgs = []
    snowflakes = []
    guild_members = {}

    for channel_message in channel_messages:
        if channel_message["id"] in snowflakes or int(
            channel_message["id"]
        ) <= int(after_snowflake):
            continue

        snowflakes.append(channel_message["id"])

        message = {
            "attachments": channel_message["attachments"],
            "timestamp": channel_message["timestamp"],
            "id": channel_message["id"],
            "edited_timestamp": channel_message["edited_timestamp"],
            "author": channel_message["author"],
            "content": channel_message["content"],
            "channel_id": str(channel_message["channel_id"]),
            "mentions": channel_message["mentions"],
            "embeds": channel_message["embeds"],
            "reactions": channel_message["reactions"],
            "type": channel_message.get("type", 0),
        }

        if message["author"]["id"] not in guild_members:
            member = get_guild_member(guild_id, message["author"]["id"])
            guild_members[message["author"]["id"]] = member
        else:
            member = guild_members[message["author"]["id"]]

        if member:
            message["author"]["nickname"] = member["nick"]
            message["author"]["avatar"] = member["avatar"]
            message["author"]["discriminator"] = member["discriminator"]
            message["author"]["username"] = member["username"]
        else:
            message["author"]["nickname"] = None

        for mention in message["mentions"]:
            if mention["id"] not in guild_members:
                author = get_guild_member(guild_id, mention["id"])
                guild_members[mention["id"]] = author
            else:
                author = guild_members[mention["id"]]

            if author:
                mention["nickname"] = author["nick"]
                mention["avatar"] = author["avatar"]
                mention["username"] = author["username"]
                mention["discriminator"] = author["discriminator"]
            else:
                mention["nickname"] = None

        msgs.append(message)

    sorted_msgs = sorted(msgs, key=lambda k: k["id"], reverse=True)
    log.info("get_channel_messages finished")
    return sorted_msgs[:50]  # only return last 50 messages in cache please


def get_guild_member(guild_id, user_id):
    key = f"/guilds/{guild_id}/members/{user_id}"
    q = redis_store.get(key)
    if not q:
        q = on_get_guild_member(key, guild_id, user_id)
    if q and not validate_not_none(key, "username", q):
        return get_user(user_id)
    return q


def get_guild_member_named(guild_id, query):
    key = f"/custom/guilds/{guild_id}/member_named/{query}"
    guild_member_id = redis_store.get("get_guild_member_named")
    if not guild_member_id:
        guild_member_id = on_get_guild_member_named(key, guild_id, query)
    if guild_member_id:
        return get_guild_member(guild_id, guild_member_id["user_id"])
    return None


def list_guild_members(guild_id):
    key = f"/guilds/{guild_id}/members"
    member_ids = redis_store.smembers(key)
    if not member_ids:
        member_ids = on_list_guild_members(key, guild_id)

    member_ids = get(key, "list_guild_members", {"guild_id": guild_id}, data_type="set")
    return [
        m for m_id in member_ids if (m := get_guild_member(guild_id, m_id["user_id"]))
    ]


def guild_clear_cache(guild_id):
    key = f"Queue/guilds/{guild_id}"
    redis_store.delete(key)


def get_guild(guild_id):
    try:
        guild_id = int(guild_id)
    except (TypeError, ValueError):
        return None

    key = f"/guilds/{guild_id}"
    q = redis_store.get(key)
    if not q:
        q = on_get_guild(key, guild_id)
    if q and not validate_not_none(key, "name", q):
        return get_guild(guild_id)
    return q


def get_user(user_id):
    key = f"/users/{user_id}"
    q = redis_store.get(key)
    if not q:
        q = on_get_user(key, user_id)
    if q and not validate_not_none(key, "username", q):
        return get_user(user_id)
    return q


def bump_user_presence_timestamp(guild_id, user_type, client_key):
    redis_key = f"MemberPresence/{guild_id}/{user_type}/{client_key}"
    redis_store.set(redis_key, "", 60)


def get_online_embed_user_keys(guild_id="*", user_type=None):
    user_type = (
        [user_type] if user_type else ["AuthenticatedUsers", "UnauthenticatedUsers"]
    )

    return {
        utype: [
            k.split("/")[-1]
            for k in redis_store.keys(f"MemberPresence/{guild_id}/{utype}/*")
        ]
        for utype in user_type
    }


def on_get_channel_messages(key, channel_id):
    channel = self.bot.get_channel(int(channel_id))
    if not channel or not isinstance(channel, discord.channel.TextChannel):
        return

    redis_store.delete(key)
    me = channel.guild.get_member(self.bot.user.id)

    messages = []
    if channel.permissions_for(me).read_messages:
        async for message in channel.history(limit=50):
            messages.append(json.dumps(format_message(message), separators=(",", ":")))

    redis_store.sadd(key, "", *messages)

    return messages


def on_get_guild_member(key, guild_id, user_id):
    if not (guild := self.bot.get_guild(int(guild_id))):
        return

    if not (member := guild.get_member(int(user_id))):
        members = guild.query_members(user_ids=[int(user_id)], cache=True)

        if not len(members):
            redis_store.set(key, "")
            enforce_expiring_key(key, 15)
            return

        member = members[0]

    formatted_member = format_user(member)
    redis_store.set(key, json.dumps(formatted_member, separators=(",", ":")))
    enforce_expiring_key(key)

    return formatted_member


def on_get_guild_member_named(key, guild_id, query):
    if not (guild := self.bot.get_guild(int(guild_id))):
        return

    result = None
    members = guild.members
    if members and len(query) > 5 and query[-5] == "#":
        potential_discriminator = query[-4:]
        result = discord.utils.get(
            members, name=query[:-5], discriminator=potential_discriminator
        )
        if not result:
            result = discord.utils.get(
                members, nick=query[:-5], discriminator=potential_discriminator
            )

    if not result:
        result = ""
    else:
        result = json.dumps({"user_id": result.id}, separators=(",", ":"))
        get_guild_member_key = f"Queue/guilds/{guild.id}/members/{result.id}"
        on_get_guild_member(get_guild_member_key, guild_id, result.id)

    redis_store.set(key, result)
    enforce_expiring_key(key)

    return result


def on_list_guild_members(key, guild_id):
    if not (guild := self.bot.get_guild(int(guild_id))):
        return

    member_ids = []
    for member in guild.members:
        member_ids.append(json.dumps({"user_id": member.id}, separators=(",", ":")))
        get_guild_member_key = f"Queue/guilds/{guild.id}/members/{member.id}"
        on_get_guild_member(get_guild_member_key, guild_id, member.id)

    redis_store.sadd(key, *member_ids)


def on_get_guild(key, guild_id):
    if not (guild := self.bot.get_guild(int(guild_id))):
        return

    if guild.me and guild.me.guild_permissions.manage_webhooks:
        try:
            server_webhooks = guild.webhooks()
        except:
            log.exception("Could not get guild webhooks")
            server_webhooks = []
    else:
        server_webhooks = []

    guild_data = format_guild(guild, server_webhooks)
    redis_store.set(key, json.dumps(guild_data, separators=(",", ":")))
    enforce_expiring_key(key)
    return guild_data


def on_get_user(key, user_id):
    if not (user := self.bot.get_user(int(user_id))):
        return

    user_formatted = {
        "id": user.id,
        "username": user.name,
        "discriminator": user.discriminator,
        "avatar": user.avatar.key if user.avatar else None,
        "bot": user.bot,
    }
    redis_store.set(key, json.dumps(user_formatted, separators=(",", ":")))
    enforce_expiring_key(key)
    return user_formatted


def enforce_expiring_key(key, ttl_override=None):
    if ttl_override:
        redis_store.expire(key, ttl_override)
        return

    ttl = redis_store.ttl(key)
    if ttl >= 0:
        new_ttl = ttl
    elif ttl == -1:
        new_ttl = 60 * 5  # 5 minutes
    else:
        new_ttl = 0

    redis_store.expire(key, new_ttl)
