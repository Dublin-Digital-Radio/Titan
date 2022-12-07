import json
import time
import logging

from flask_redis import FlaskRedis

log = logging.getLogger(__name__)

redis_store = FlaskRedis(charset="utf-8", decode_responses=True)


def get(key, resource, params, *, data_type="str"):
    key = "Queue" + key
    _get = redis_store.smembers if data_type == "set" else redis_store.get

    data = _get(key)
    payload = {"key": key, "resource": resource, "params": params}

    loop_count = 0
    while (not data and data != "") and loop_count < 50:
        if loop_count % 25 == 0:
            redis_store.publish("discord-api-req", json.dumps(payload))
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
    key = f"/channels/{channel_id}/messages"

    q = get(key, "get_channel_messages", {"channel_id": channel_id}, data_type="set")
    if not q:
        log.warning("Got none from channel messages")
        return []

    msgs = []
    snowflakes = []
    guild_members = {}
    for x in q:
        if x["id"] in snowflakes or int(x["id"]) <= int(after_snowflake):
            continue
        snowflakes.append(x["id"])
        message = {
            "attachments": x["attachments"],
            "timestamp": x["timestamp"],
            "id": x["id"],
            "edited_timestamp": x["edited_timestamp"],
            "author": x["author"],
            "content": x["content"],
            "channel_id": str(x["channel_id"]),
            "mentions": x["mentions"],
            "embeds": x["embeds"],
            "reactions": x["reactions"],
            "type": x.get("type", 0),
        }
        if message["author"]["id"] not in guild_members:
            member = get_guild_member(guild_id, message["author"]["id"])
            guild_members[message["author"]["id"]] = member
        else:
            member = guild_members[message["author"]["id"]]
        message["author"]["nickname"] = None
        if member:
            message["author"]["nickname"] = member["nick"]
            message["author"]["avatar"] = member["avatar"]
            message["author"]["discriminator"] = member["discriminator"]
            message["author"]["username"] = member["username"]
        for mention in message["mentions"]:
            if mention["id"] not in guild_members:
                author = get_guild_member(guild_id, mention["id"])
                guild_members[mention["id"]] = author
            else:
                author = guild_members[mention["id"]]
            mention["nickname"] = None
            if author:
                mention["nickname"] = author["nick"]
                mention["avatar"] = author["avatar"]
                mention["username"] = author["username"]
                mention["discriminator"] = author["discriminator"]
        msgs.append(message)
    sorted_msgs = sorted(msgs, key=lambda k: k["id"], reverse=True)
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
    members = []
    for member_id in member_ids:
        member = get_guild_member(guild_id, member_id["user_id"])
        if member:
            members.append(member)
    return members


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
