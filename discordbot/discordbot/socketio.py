import logging

import discord
import socketio

from discordbot.utils import (
    format_channel,
    format_formatted_emojis,
    format_guild,
    format_message,
    format_role,
    format_user,
)

log = logging.getLogger(__name__)


class SocketIOInterface:
    def __init__(self, redis_uri):
        self.io = socketio.AsyncRedisManager(redis_uri, write_only=True, channel="flask-socketio")

    async def on_mess(self, action, message):
        if not message.guild:
            return

        await self.io.emit(
            action,
            data=format_message(message),
            room=f"CHANNEL_{message.channel.id}",
            namespace="/gateway",
        )

    async def on_message(self, message):
        await self.on_mess("MESSAGE_CREATE", message)

    async def on_message_delete(self, message):
        await self.on_mess("MESSAGE_DELETE", message)

    async def on_message_update(self, message):
        await self.on_mess("MESSAGE_UPDATE", message)

    async def on_reaction_add(self, message):
        await self.on_mess("MESSAGE_REACTION_ADD", message)

    async def on_reaction_remove(self, message):
        await self.on_mess("MESSAGE_REACTION_REMOVE", message)

    async def on_reaction_clear(self, message):
        await self.on_mess("MESSAGE_REACTION_REMOVE_ALL", message)

    async def on_guild_member(self, message, member):
        await self.io.emit(
            message,
            data=format_user(member),
            room=f"GUILD_{member.guild.id}",
            namespace="/gateway",
        )

    async def on_guild_member_add(self, member):
        await self.on_guild_member("GUILD_MEMBER_ADD", member)

    async def on_guild_member_remove(self, member):
        await self.on_guild_member("GUILD_MEMBER_REMOVE", member)

    async def on_guild_member_update(self, member):
        await self.on_guild_member("GUILD_MEMBER_UPDATE", member)

    async def on_guild_emojis_update(self, emojis):
        if len(emojis) == 0:
            return

        await self.io.emit(
            "GUILD_EMOJIS_UPDATE",
            data=format_formatted_emojis(emojis),
            room=f"GUILD_{emojis[0].guild.id}",
            namespace="/gateway",
        )

    async def on_channel(self, channel, message):
        if str(channel.type) != "text":
            return

        await self.io.emit(
            message,
            data=format_channel(channel),
            room=f"GUILD_{channel.guild.id}",
            namespace="/gateway",
        )

    async def on_channel_delete(self, channel):
        await self.on_channel(channel, "CHANNEL_DELETE")

    async def on_channel_create(self, channel):
        await self.on_channel(channel, "CHANNEL_CREATE")

    async def on_channel_update(self, channel):
        if not isinstance(channel, discord.channel.TextChannel) and not isinstance(
            channel, discord.channel.CategoryChannel
        ):
            return

        await self.io.emit(
            "CHANNEL_UPDATE",
            data=format_channel(channel),
            room=f"GUILD_{channel.guild.id}",
            namespace="/gateway",
        )

    async def on_guild_update(self, guild):
        await self.io.emit(
            "GUILD_UPDATE",
            data=format_guild(guild),
            room=f"GUILD_{guild.id}",
            namespace="/gateway",
        )

    async def on_guild_role(self, role, message):
        await self.io.emit(
            message,
            data=format_role(role),
            room=f"GUILD_{role.guild.id}",
            namespace="/gateway",
        )

    async def on_guild_role_create(self, role):
        await self.on_guild_role(role, "GUILD_ROLE_CREATE")

    async def on_guild_role_update(self, role):
        await self.on_guild_role(role, "GUILD_ROLE_UPDATE")

    async def on_guild_role_delete(self, role):
        await self.on_guild_role(role, "GUILD_ROLE_DELETE")
