import json
import time
import logging

import redis

log = logging.getLogger(__name__)

redis_store = redis.Redis()


def init_redis(url):
    global redis_store
    redis_store = redis.Redis.from_url(url, decode_responses=True)


def get(key, resource, params, *, data_type="str"):
    key = "Queue" + key
    _get = redis_store.smembers if data_type == "set" else redis_store.get

    data = _get(key)

    loop_count = 0
    while (not data and data != "") and loop_count < 50:
        if loop_count % 25 == 0:
            redis_store.publish(
                "discord-api-req",
                json.dumps({"key": key, "resource": resource, "params": params}),
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
    channel_messages = get(
        f"/channels/{channel_id}/messages",
        "get_channel_messages",
        {"channel_id": channel_id, "limit": 50},
        data_type="set",
    )
    if not channel_messages:
        log.warning("Got none from channel messages")
        return []
    log.info("get_channel_messages : got %s messages", len(channel_messages))

    msgs = []
    snowflakes = []
    guild_members = {}

    for channel_message in channel_messages:
        if channel_message["id"] in snowflakes or int(channel_message["id"]) <= int(
            after_snowflake
        ):
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
    q = get(key, "get_guild_member", {"guild_id": guild_id, "user_id": user_id})
    if q and not validate_not_none(key, "username", q):
        return get_user(user_id)
    return q


def get_guild_member_named(guild_id, query):
    key = f"/custom/guilds/{guild_id}/member_named/{query}"
    guild_member_id = get(key, "get_guild_member_named", {"guild_id": guild_id, "query": query})
    if guild_member_id:
        return get_guild_member(guild_id, guild_member_id["user_id"])
    return None


def list_guild_members(guild_id):
    key = f"/guilds/{guild_id}/members"
    member_ids = get(key, "list_guild_members", {"guild_id": guild_id}, data_type="set")
    return [m for m_id in member_ids if (m := get_guild_member(guild_id, m_id["user_id"]))]


def guild_clear_cache(guild_id):
    key = f"Queue/guilds/{guild_id}"
    redis_store.delete(key)


def get_guild(guild_id):
    try:
        guild_id = int(guild_id)
    except (TypeError, ValueError):
        return None

    key = f"/guilds/{guild_id}"
    q = get(key, "get_guild", {"guild_id": guild_id})
    if q and not validate_not_none(key, "name", q):
        return get_guild(guild_id)
    return q


def get_user(user_id):
    key = f"/users/{user_id}"
    q = get(key, "get_user", {"user_id": user_id})
    if q and not validate_not_none(key, "username", q):
        return get_user(user_id)
    return q


def bump_user_presence_timestamp(guild_id, user_type, client_key):
    redis_key = f"MemberPresence/{guild_id}/{user_type}/{client_key}"
    redis_store.set(redis_key, "", 60)


def get_online_embed_user_keys(guild_id="*", user_type=None):
    user_type = [user_type] if user_type else ["AuthenticatedUsers", "UnauthenticatedUsers"]

    return {
        utype: [
            k.split("/")[-1] for k in redis_store.keys(f"MemberPresence/{guild_id}/{utype}/*")
        ]
        for utype in user_type
    }
