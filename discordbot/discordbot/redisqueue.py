import re
import json
import asyncio
import logging
from pprint import pformat

import async_timeout
import discord
import redis.exceptions
from redis.asyncio.client import Redis
from redis.asyncio.connection import ConnectionPool
from redis.asyncio.retry import Retry
from redis.backoff import ConstantBackoff
from redis.exceptions import ConnectionError, TimeoutError

from discordbot.utils import format_guild, format_message, format_user

log = logging.getLogger(__name__)


class UnreadyConnection:
    def __getattr__(self, item):
        raise Exception(f"accessing {item} before RedisQueue.connect()")


class RedisQueue:
    def __init__(self, bot, redis_uri):
        self.bot = bot
        self.redis_uri = redis_uri
        self.connection = UnreadyConnection()

    async def connect(self):
        connection_pool = ConnectionPool.from_url(self.redis_uri)
        self.connection = Redis(
            connection_pool=connection_pool,
            retry_on_error=[ConnectionError, TimeoutError],
            retry=Retry(backoff=ConstantBackoff(2), retries=100),
            health_check_interval=60,  # seconds
        )
        log.info("Connected to redis")

    async def subscribe(self):
        await self.bot.wait_until_ready()

        subscriber = self.connection.pubsub()
        await subscriber.subscribe("discord-api-req")

        while True:
            if not self.bot.is_ready() or self.bot.is_closed():
                await asyncio.sleep(1)
                continue
            try:
                async with async_timeout.timeout(1):
                    try:
                        reply = await subscriber.get_message(
                            ignore_subscribe_messages=True
                        )
                    except ConnectionError:
                        log.error("Redis connection lost... reconnecting")
                        await self.connect()
                        continue

                    if reply is None:
                        continue

                    request = json.loads(reply["data"].decode())
                    self.dispatch(
                        request["resource"], request["key"], request["params"]
                    )
                    await asyncio.sleep(0.01)
            except asyncio.TimeoutError:
                pass

    def dispatch(self, event, key, params):
        method = "on_" + event
        if hasattr(self, method):
            self.bot.loop.create_task(self._run_event(method, key, params))
        else:
            log.error("cannot find method '%s'", method)

    async def _run_event(self, event, key, params):
        log.info("_run_event '%s': '%s': '%s'", event, key, pformat(params))

        try:
            await getattr(self, event)(key, params)
        except redis.exceptions.ConnectionError:
            log.error("Redis connection error")
            await self.connect()
        except asyncio.CancelledError:
            pass
        except Exception:
            try:
                log.exception(
                    "error running event\n  '%s' : '%s' : '%s'", pformat(params)
                )
            except asyncio.CancelledError:
                pass

    async def set_scan_json(self, key, dict_key, dict_value_pattern):
        if not await self.connection.exists(key):
            return None, None

        for the_member in await self.connection.smembers(key):
            # the_member = await member
            if not the_member:
                continue

            parsed = json.loads(the_member)
            if re.match(str(dict_value_pattern), str(parsed[dict_key])):
                return the_member, parsed

        return None, None

    async def enforce_expiring_key(self, key, ttl_override=None):
        if ttl_override:
            await self.connection.expire(key, ttl_override)
            return

        ttl = await self.connection.ttl(key)
        if ttl >= 0:
            new_ttl = ttl
        elif ttl == -1:
            new_ttl = 60 * 5  # 5 minutes
        else:
            new_ttl = 0

        await self.connection.expire(key, new_ttl)

    async def on_get_channel_messages(self, key, params):
        channel = self.bot.get_channel(int(params["channel_id"]))
        if not channel or not isinstance(channel, discord.channel.TextChannel):
            return

        await self.connection.delete(key)
        me = channel.guild.get_member(self.bot.user.id)

        messages = []
        if channel.permissions_for(me).read_messages:
            async for message in channel.history(limit=50):
                messages.append(
                    json.dumps(format_message(message), separators=(",", ":"))
                )

        await self.connection.sadd(key, "", *messages)

    async def push_message(self, message):
        if not message.guild:
            return

        key = f"Queue/channels/{message.channel.id}/messages"
        if not await self.connection.exists(key):
            return

        message = format_message(message)
        await self.connection.sadd(key, json.dumps(message, separators=(",", ":")))

    async def delete_message(self, message):
        if not message.guild:
            return

        key = f"Queue/channels/{message.channel.id}/messages"
        if not await self.connection.exists(key):
            return

        unformatted_item, formatted_item = await self.set_scan_json(
            key, "id", message.id
        )
        if formatted_item:
            await self.connection.srem(key, unformatted_item)

    async def update_message(self, message):
        await self.delete_message(message)
        await self.push_message(message)

    async def on_get_guild_member(self, key, params):
        if not (guild := self.bot.get_guild(int(params["guild_id"]))):
            return

        if not (member := guild.get_member(int(params["user_id"]))):
            members = await guild.query_members(
                user_ids=[int(params["user_id"])], cache=True
            )

            if not len(members):
                await self.connection.set(key, "")
                await self.enforce_expiring_key(key, 15)
                return

            member = members[0]

        await self.connection.set(
            key, json.dumps(format_user(member), separators=(",", ":"))
        )
        await self.enforce_expiring_key(key)

    async def on_get_guild_member_named(self, key, params):
        if not (guild := self.bot.get_guild(int(params["guild_id"]))):
            return

        query = params["query"]
        members = None
        if guild.members and len(query) > 5 and query[-5] == "#":
            potential_discriminator = query[-4:]
            members = discord.utils.get(
                guild.members, name=query[:-5], discriminator=potential_discriminator
            )
            if not members:
                members = discord.utils.get(
                    guild.members,
                    nick=query[:-5],
                    discriminator=potential_discriminator,
                )

        if not members:
            result = ""
        else:
            result = json.dumps({"user_id": (members.id)}, separators=(",", ":"))
            get_guild_member_key = f"Queue/guilds/{guild.id}/members/{members.id}"
            get_guild_member_param = {"guild_id": guild.id, "user_id": members.id}
            await self.on_get_guild_member(get_guild_member_key, get_guild_member_param)

        await self.connection.set(key, result)
        await self.enforce_expiring_key(key)

    async def on_list_guild_members(self, key, params):
        if not (guild := self.bot.get_guild(int(params["guild_id"]))):
            return

        member_ids = []
        for member in guild.members:
            member_ids.append(json.dumps({"user_id": member.id}, separators=(",", ":")))
            get_guild_member_key = f"Queue/guilds/{guild.id}/members/{member.id}"
            get_guild_member_param = {"guild_id": guild.id, "user_id": member.id}
            await self.on_get_guild_member(get_guild_member_key, get_guild_member_param)

        await self.connection.sadd(key, *member_ids)

    async def add_member(self, member):
        if await self.connection.exists(f"Queue/guilds/{member.guild.id}/members"):
            await self.connection.sadd(
                f"Queue/guilds/{member.guild.id}/members",
                json.dumps({"user_id": member.id}, separators=(",", ":")),
            )

        get_guild_member_key = f"Queue/guilds/{member.guild.id}/members/{member.id}"
        get_guild_member_param = {"guild_id": member.guild.id, "user_id": member.id}
        await self.on_get_guild_member(get_guild_member_key, get_guild_member_param)

    async def remove_member(self, member, guild=None):
        if not guild:
            guild = member.guild

        await self.connection.srem(
            f"Queue/guilds/{guild.id}/members",
            json.dumps({"user_id": member.id}, separators=(",", ":")),
        )
        await self.connection.delete(f"Queue/guilds/{guild.id}/members/{member.id}")

    async def update_member(self, member):
        await self.remove_member(member)
        await self.add_member(member)

    async def ban_member(self, guild, user):
        await self.remove_member(user, guild)

    async def on_get_guild(self, key, params):
        if not (guild := self.bot.get_guild(int(params["guild_id"]))):
            return

        if guild.me and guild.me.guild_permissions.manage_webhooks:
            try:
                server_webhooks = await guild.webhooks()
            except:
                log.exception("Could not get guild webhooks")
                server_webhooks = []
        else:
            server_webhooks = []

        await self.connection.set(
            key, json.dumps(format_guild(guild, server_webhooks), separators=(",", ":"))
        )
        await self.enforce_expiring_key(key)

    async def delete_guild(self, guild):
        await self.connection.delete(f"Queue/guilds/{guild.id}")

    async def update_guild(self, guild):
        key = f"Queue/guilds/{guild.id}"

        if await self.connection.exists(key):
            await self.delete_guild(guild)
            await self.on_get_guild(key, {"guild_id": guild.id})
        await self.enforce_expiring_key(key)

    async def on_get_user(self, key, params):
        if not (user := self.bot.get_user(int(params["user_id"]))):
            return

        user_formatted = {
            "id": user.id,
            "username": user.name,
            "discriminator": user.discriminator,
            "avatar": user.avatar.key if user.avatar else None,
            "bot": user.bot,
        }
        await self.connection.set(
            key, json.dumps(user_formatted, separators=(",", ":"))
        )
        await self.enforce_expiring_key(key)
