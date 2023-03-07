import sys
import asyncio
import logging
from collections import deque

import discord

# from raven import Client as RavenClient
# import raven
from config import config
from redis.exceptions import ConnectionError

from discordbot import commands, redis_cache
from discordbot.poststats import BotsDiscordPw, DiscordBotsOrg
from discordbot.socketio import SocketIOInterface

# try:
#     raven_client = RavenClient(config["sentry-dsn"])
# except raven.exceptions.InvalidDsn:
#     pass

intents = discord.Intents.default()
intents.message_content = True


def setup_logger(shard_ids=None):
    # shard_ids = "-".join(str(x) for x in shard_ids) if shard_ids is not None else ""
    handler = logging.StreamHandler(stream=sys.stdout)
    if discord.utils.stream_supports_colour(handler.stream):
        format_cls = discord.utils._ColourFormatter
    else:
        format_cls = logging.Formatter

    level = logging.INFO
    formatter = format_cls(
        fmt="%(levelname)s %(name)s %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S %p",
    )
    discord.utils.setup_logging(
        handler=handler, formatter=formatter, level=level, root=True
    )

    return logging.getLogger("TitanBot")


def _handle_task_result(task: asyncio.Task) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        pass  # Task cancellation should not be logged as an error.
    except Exception:  # pylint: disable=broad-except
        logging.exception("Exception raised by task = %r", task)


class Titan(discord.AutoShardedClient):
    def __init__(self, shard_ids=None, shard_count=None):
        super().__init__(
            shard_ids=shard_ids,
            shard_count=shard_count,
            max_messages=10000,
            intents=intents,
            chunk_guilds_at_startup=False,
            activity=discord.Game(
                name="Embed your Discord server! Visit https://TitanEmbeds.com/"
            ),
        )
        self.log = setup_logger(shard_ids)
        self.http.user_agent += " TitanEmbeds-Bot"
        redis_cache.init_redis(config["redis-uri"])
        self.socketio = SocketIOInterface(config["redis-uri"])

        # List of msg ids to prevent duplicate delete
        self.delete_list = deque(maxlen=100)
        self.discordBotsOrg = None
        self.botsDiscordPw = None

        self.redis_sub_task = None
        self.post_stats_task = None

    def _cleanup(self):
        try:
            self.loop.run_until_complete(self.logout())
        except:  # Can be ignored
            self.log.exception("run_until_complete")
            pass

        pending = asyncio.Task.all_tasks()
        gathered = asyncio.gather(*pending)

        try:
            gathered.cancel()
            self.loop.run_until_complete(gathered)
            gathered.exception()
        except:  # Can be ignored
            self.log.exception("gather")
            pass

    async def start(self, token: str, *, reconnect: bool = True) -> None:
        await redis_cache.connection.connect()
        await super().start(config["bot-token"], reconnect=reconnect)

    async def on_shard_ready(self, shard_id):
        self.log.info("Titan [DiscordBot]")
        self.log.info("Logged in as the following user:")
        self.log.info(self.user.name)
        self.log.info(self.user.id)
        self.log.info("------")
        self.log.info("Shard count: " + str(self.shard_count))
        self.log.info("Shard id: " + str(shard_id))
        self.log.info("------")

        self.redis_sub_task = self.loop.create_task(
            redis_cache.connection.subscribe()
        )
        self.redis_sub_task.add_done_callback(_handle_task_result)

        if config["discord-bots-org-token"]:
            self.discordBotsOrg = DiscordBotsOrg(
                self.user.id, config["discord-bots-org-token"]
            )
        if config["bots-discord-pw-token"]:
            self.botsDiscordPw = BotsDiscordPw(
                self.user.id, config["bots-discord-pw-token"]
            )
        if config["discord-bots-org-token"] or config["bots-discord-pw-token"]:
            self.post_stats_task = self.loop.create_task(self.auto_post_stats())
            self.post_stats_task.add_done_callback(_handle_task_result)

    async def on_message(self, message):
        await self.socketio.on_message(message)
        try:
            await redis_cache.connection.push_message(message)
        except ConnectionError:
            self.log.error("Retrying one time after redis connection error")
            await redis_cache.connection.connect()
            await redis_cache.connection.push_message(message)

        # See if there is a command we recognise
        msg = message.content.split()
        if len(msg) <= 1:
            return

        msg_cmd = msg[1].lower()
        if msg_cmd == "__init__":
            return

        # making sure there is actually stuff in the message and have arguments
        # and check if it is sent in server (not PM)
        if (
            message.guild
            # make sure it is mention
            and (msg[0] in [f"<@{self.user.id}>", f"<@!{self.user.id}>"])
            and getattr(commands, msg_cmd, None)
        ):
            self.log.info("running message %s", msg_cmd)
            async with message.channel.typing():  # this looks nice
                # actually run cmd, passing in msg obj
                await getattr(commands, msg_cmd)(message)

    async def on_message_edit(self, message_before, message_after):
        await redis_cache.connection.update_message(message_after)
        await self.socketio.on_message_update(message_after)

    async def on_message_delete(self, message):
        self.delete_list.append(message.id)
        await redis_cache.connection.delete_message(message)
        await self.socketio.on_message_delete(message)

    async def on_reaction_add(self, reaction, user):
        await redis_cache.connection.update_message(reaction.message)
        await self.socketio.on_reaction_add(reaction.message)

    async def on_reaction_remove(self, reaction, user):
        await redis_cache.connection.update_message(reaction.message)
        await self.socketio.on_reaction_remove(reaction.message)

    async def on_reaction_clear(self, message, reactions):
        await redis_cache.connection.update_message(message)
        await self.socketio.on_reaction_clear(message)

    async def on_guild_join(self, guild):
        await redis_cache.connection.update_guild(guild)
        await self.on_get_guild(guild.id)
        await self.postStats()

    async def on_guild_remove(self, guild):
        await redis_cache.connection.delete_guild(guild)
        await self.postStats()

    async def on_guild_update(self, guildbefore, guildafter):
        await redis_cache.connection.update_guild(guildafter)
        await self.on_get_guild(guildafter.id)
        await self.socketio.on_guild_update(guildafter)

    async def on_guild_role_create(self, role):
        if role.name == self.user.name and role.managed:
            await asyncio.sleep(2)
        await redis_cache.connection.update_guild(role.guild)
        await self.on_get_guild(role.guild.id)
        await self.socketio.on_guild_role_create(role)

    async def on_guild_role_delete(self, role):
        if role.guild.me not in role.guild.members:
            return
        await redis_cache.connection.update_guild(role.guild)
        await self.on_get_guild(role.guild.id)
        await self.socketio.on_guild_role_delete(role)

    async def on_guild_role_update(self, rolebefore, roleafter):
        await redis_cache.connection.update_guild(roleafter.guild)
        await self.on_get_guild(roleafter.guild.id)
        await self.socketio.on_guild_role_update(roleafter)

    async def on_guild_channel_delete(self, channel):
        if channel.guild:
            await redis_cache.connection.update_guild(channel.guild)
            await self.on_get_guild(channel.guild.id)
            await self.socketio.on_channel_delete(channel)

    async def on_guild_channel_create(self, channel):
        if channel.guild:
            await redis_cache.connection.update_guild(channel.guild)
            await self.on_get_guild(channel.guild.id)
            await self.socketio.on_channel_create(channel)

    async def on_guild_channel_update(self, channelbefore, channelafter):
        await redis_cache.connection.update_guild(channelafter.guild)
        await self.on_get_guild(channelafter.guild.id)
        await self.socketio.on_channel_update(channelafter)

    async def on_member_join(self, member):
        await redis_cache.connection.add_member(member)
        await self.on_get_guild_member(member.guild.id, member.id)
        await self.socketio.on_guild_member_add(member)

    async def on_member_remove(self, member):
        await redis_cache.connection.remove_member(member)
        await self.socketio.on_guild_member_remove(member)

    async def on_member_update(self, memberbefore, memberafter):
        await redis_cache.connection.update_member(memberafter)
        await self.socketio.on_guild_member_update(memberafter)

    async def on_member_ban(self, guild, user):
        if self.user.id == user.id:
            return
        await redis_cache.connection.ban_member(guild, user)

    async def on_guild_emojis_update(self, guild, before, after):
        await redis_cache.connection.update_guild(guild)
        await self.on_get_guild(guild.id)
        await self.socketio.on_guild_emojis_update(
            after if len(after) else before
        )

    # async def on_webhooks_update(self, channel):
    #     await redis_cache.connection.update_guild(channel.guild)
    #     await self.on_get_guild(channel.guild.id)

    async def on_raw_message_edit(self, payload):
        message_id = payload.message_id
        data = payload.data
        if self.in_messages_cache(int(message_id)):
            return

        channel = self.get_channel(int(data["channel_id"]))
        me = channel.guild.get_member(self.user.id)
        if not channel.permissions_for(me).read_messages:
            return

        message = await channel.fetch_message(int(message_id))
        await self.on_message_edit(None, message)

    async def on_raw_message_delete(self, payload):
        message_id = payload.message_id
        channel_id = payload.channel_id
        if self.in_messages_cache(int(message_id)):
            return

        await asyncio.sleep(1)
        await self.process_raw_message_delete(int(message_id), int(channel_id))

    async def raw_bulk_message_delete(self, payload):
        await asyncio.sleep(1)
        for msg_id in [int(x) for x in payload.message_ids]:
            if not self.in_messages_cache(msg_id):
                await self.process_raw_message_delete(
                    msg_id, int(payload.channel_id)
                )

    async def process_raw_message_delete(self, msg_id, channel_id):
        if msg_id in self.delete_list:
            self.delete_list.remove(msg_id)
            return

        channel = self.get_channel(int(channel_id))
        data = {
            "content": "What fun is there in making sense?",
            "type": 0,
            "edited_timestamp": None,
            "id": msg_id,
            "channel_id": channel_id,
            "timestamp": "2017-01-15T02:59:58+00:00",
            "attachments": [],
            "embeds": [],
            "pinned": False,
            "mention_everyone": False,
            "tts": False,
            "nonce": None,
        }
        # Procreate a fake message object
        msg = discord.Message(
            channel=channel, state=self._connection, data=data
        )
        await self.on_message_delete(msg)

    async def on_raw_reaction_add(self, payload):
        message_id = payload.message_id
        if self.in_messages_cache(message_id):
            return

        channel = self.get_channel(payload.channel_id)
        me = channel.guild.get_member(self.user.id)
        if not channel.permissions_for(me).read_messages:
            return

        message = await channel.fetch_message(message_id)
        if len(message.reactions):
            await self.on_reaction_add(message.reactions[0], None)

    async def on_raw_reaction_remove(self, payload):
        message_id = payload.message_id
        if self.in_messages_cache(message_id):
            return

        partial = payload.emoji
        emoji = self._connection._upgrade_partial_emoji(partial)
        channel = self.get_channel(payload.channel_id)
        me = channel.guild.get_member(self.user.id)
        if not channel.permissions_for(me).read_messages:
            return

        message = await channel.fetch_message(message_id)
        message._add_reaction(
            {"me": payload.user_id == self.user.id}, emoji, payload.user_id
        )
        reaction = message._remove_reaction({}, emoji, payload.user_id)

        await self.on_reaction_remove(reaction, None)

    async def on_raw_reaction_clear(self, payload):
        message_id = payload.message_id
        if self.in_messages_cache(message_id):
            return

        channel = self.get_channel(payload.channel_id)
        me = channel.guild.get_member(self.user.id)
        if not channel.permissions_for(me).read_messages:
            return

        message = await channel.fetch_message(message_id)
        await self.on_reaction_clear(message, [])

    async def on_socket_response(self, msg):
        if not (msg.get("op") == 0 and msg.get("t") == "WEBHOOKS_UPDATE"):
            return

        guild_id = int(msg["d"]["guild_id"])
        guild = self.get_guild(guild_id)
        if guild:
            await redis_cache.connection.update_guild(guild)
            await self.on_get_guild(guild.id)

    def in_messages_cache(self, msg_id):
        return any(x.id == msg_id for x in self._connection._messages)

    async def auto_post_stats(self):
        while not self.is_closed():
            await self.postStats()
            await asyncio.sleep(1800)

    async def postStats(self):
        count = len(self.guilds)
        shard_count = self.shard_count
        shard_id = self.shard_id
        await self.discordBotsOrg.post(count, shard_count, shard_id)
        await self.botsDiscordPw.post(count, shard_count, shard_id)
