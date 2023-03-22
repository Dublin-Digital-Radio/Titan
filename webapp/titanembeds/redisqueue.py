import logging
import socket

import requests

from config import config


log = logging.getLogger(__name__)


# old_getaddrinfo = socket.getaddrinfo
#
#
# def new_getaddrinfo(*args, **kwargs):
#     responses = old_getaddrinfo(*args, **kwargs)
#     return [
#         response for response in responses if response[0] == socket.AF_INET6
#     ]
#
#
# socket.getaddrinfo = new_getaddrinfo


def get_url():
    if config["bot-http-over-ipv6"]:
        ipv6_addr = get_ipv6_addr(
            config["bot-http-url"], config["bot-http-port"]
        )
        if not ipv6_addr:
            return None
        return f'http://[{ipv6_addr}]:{config["bot-http-port"]}'
    else:
        return f'http://{config["bot-http-url"]}:{config["bot-http-port"]}'


def get_ipv6_addr(host, port):
    log.info("looking up %s:%s", host, port)
    addrs = socket.getaddrinfo(host, port)
    # ipv4_addrs = [addr[4][0] for addr in addrs if addr[0] == socket.AF_INET]
    ipv6_addrs = [addr[4][0] for addr in addrs if addr[0] == socket.AF_INET6]
    return ipv6_addrs[0] if ipv6_addrs else None


def http_get(path):
    url = f"{get_url()}/{path}"
    log.info("GET %s", url)
    response = requests.get(url)

    try:
        json = response.json()
    except requests.exceptions.JSONDecodeError:
        log.error("No valid json in response")
        return None

    log.info("response:\n%s", json)
    return json


def get_channel_messages(guild_id, channel_id, after_snowflake=0):
    log.info("get_channel_messages")
    response = http_get(f"channel_messages/{channel_id}")
    channel_messages = response if response else []

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
    return http_get(f"guild/{guild_id}/member/{user_id}")


def get_guild_member_named(guild_id, query):
    guild_member_id = http_get(f"guild/{guild_id}/member-name/{query}")

    if guild_member_id:
        return get_guild_member(guild_id, guild_member_id["user_id"])

    return None


def list_guild_members(guild_id):
    member_ids = http_get(f"guild/{guild_id}/members")
    if not member_ids:
        return []

    return [
        m
        for m_id in member_ids
        if (m := get_guild_member(guild_id, m_id["user_id"]))
    ]


def get_guild(guild_id):
    try:
        guild_id = int(guild_id)
    except (TypeError, ValueError):
        return None

    return http_get(f"guild/{guild_id}")


def get_user(user_id):
    return http_get(f"user/{user_id}")
