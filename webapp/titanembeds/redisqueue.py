from functools import wraps
import logging

import requests

from config import config


log = logging.getLogger(__name__)


def catch_json_exception(func):
    @wraps(func)
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.JSONDecodeError:
            log.exception("Could not decode json")
            return {}

    return inner


def get_url():
    return f'{config["bot-http-url"]}:{config["bot-http-port"]}'


def get_channel_messages(guild_id, channel_id, after_snowflake=0):
    log.info("get_channel_messages")
    response = requests.get(f"{get_url()}/channel_messages/{channel_id}")
    try:
        channel_messages = response.json()
    except requests.exceptions.JSONDecodeError:
        log.exception("No JSON data returned")
        channel_messages = []

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


@catch_json_exception
def get_guild_member(guild_id, user_id):
    response = requests.get(f"{get_url()}/guild/{guild_id}/member/{user_id}")
    return response.json()


@catch_json_exception
def get_guild_member_named(guild_id, query):
    response = requests.get(f"{get_url()}/guild/{guild_id}/member-name/{query}")
    guild_member_id = response.json()

    if guild_member_id:
        return get_guild_member(guild_id, guild_member_id["user_id"])

    return None


@catch_json_exception
def list_guild_members(guild_id):
    response = requests.get(f"{get_url()}/guild/{guild_id}/members")
    member_ids = response.json()

    return [
        m
        for m_id in member_ids
        if (m := get_guild_member(guild_id, m_id["user_id"]))
    ]


@catch_json_exception
def get_guild(guild_id):
    try:
        guild_id = int(guild_id)
    except (TypeError, ValueError):
        return None

    response = requests.get(f"{get_url()}/guild/{guild_id}")
    return response.json()


@catch_json_exception
def get_user(user_id):
    response = requests.get(f"{get_url()}/user/{user_id}")
    return response.json()
