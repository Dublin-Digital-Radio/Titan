import discord
import socketio
from discordbot.utils import (
    get_formatted_channel,
    get_formatted_emojis,
    get_formatted_guild,
    get_formatted_message,
    get_formatted_role,
    get_formatted_user,
)


class SocketIOInterface:
    def __init__(self, bot, redis_uri):
        self.io = socketio.AsyncRedisManager(redis_uri, write_only=True, channel="flask-socketio")
        self.bot = bot

    async def on_message(self, message):
        if not message.guild:
            return

        await self.io.emit(
            "MESSAGE_CREATE",
            data=get_formatted_message(message),
            room=str("CHANNEL_" + str(message.channel.id)),
            namespace="/gateway",
        )

    async def on_message_delete(self, message):
        if not message.guild:
            return

        await self.io.emit(
            "MESSAGE_DELETE",
            data=get_formatted_message(message),
            room=str("CHANNEL_" + str(message.channel.id)),
            namespace="/gateway",
        )

    async def on_message_update(self, message):
        if not message.guild:
            return

        await self.io.emit(
            "MESSAGE_UPDATE",
            data=get_formatted_message(message),
            room=str("CHANNEL_" + str(message.channel.id)),
            namespace="/gateway",
        )

    async def on_reaction_add(self, message):
        if not message.guild:
            return

        await self.io.emit(
            "MESSAGE_REACTION_ADD",
            data=get_formatted_message(message),
            room=str("CHANNEL_" + str(message.channel.id)),
            namespace="/gateway",
        )

    async def on_reaction_remove(self, message):
        if not message.guild:
            return

        await self.io.emit(
            "MESSAGE_REACTION_REMOVE",
            data=get_formatted_message(message),
            room=str("CHANNEL_" + str(message.channel.id)),
            namespace="/gateway",
        )

    async def on_reaction_clear(self, message):
        if not message.guild:
            return

        await self.io.emit(
            "MESSAGE_REACTION_REMOVE_ALL",
            data=get_formatted_message(message),
            room=str("CHANNEL_" + str(message.channel.id)),
            namespace="/gateway",
        )

    async def on_guild_member_add(self, member):
        await self.io.emit(
            "GUILD_MEMBER_ADD",
            data=get_formatted_user(member),
            room=str("GUILD_" + str(member.guild.id)),
            namespace="/gateway",
        )

    async def on_guild_member_remove(self, member):
        await self.io.emit(
            "GUILD_MEMBER_REMOVE",
            data=get_formatted_user(member),
            room=str("GUILD_" + str(member.guild.id)),
            namespace="/gateway",
        )

    async def on_guild_member_update(self, member):
        await self.io.emit(
            "GUILD_MEMBER_UPDATE",
            data=get_formatted_user(member),
            room=str("GUILD_" + str(member.guild.id)),
            namespace="/gateway",
        )

    async def on_guild_emojis_update(self, emojis):
        if len(emojis) == 0:
            return

        await self.io.emit(
            "GUILD_EMOJIS_UPDATE",
            data=get_formatted_emojis(emojis),
            room=str("GUILD_" + str(emojis[0].guild.id)),
            namespace="/gateway",
        )

    async def on_guild_update(self, guild):
        await self.io.emit(
            "GUILD_UPDATE",
            data=get_formatted_guild(guild),
            room=str("GUILD_" + str(guild.id)),
            namespace="/gateway",
        )

    async def on_channel_delete(self, channel):
        if str(channel.type) != "text":
            return

        await self.io.emit(
            "CHANNEL_DELETE",
            data=get_formatted_channel(channel),
            room=str("GUILD_" + str(channel.guild.id)),
            namespace="/gateway",
        )

    async def on_channel_create(self, channel):
        if str(channel.type) != "text":
            return

        await self.io.emit(
            "CHANNEL_CREATE",
            data=get_formatted_channel(channel),
            room=str("GUILD_" + str(channel.guild.id)),
            namespace="/gateway",
        )

    async def on_channel_update(self, channel):
        if not isinstance(channel, discord.channel.TextChannel) and not isinstance(
            channel, discord.channel.CategoryChannel
        ):
            return

        await self.io.emit(
            "CHANNEL_UPDATE",
            data=get_formatted_channel(channel),
            room=str("GUILD_" + str(channel.guild.id)),
            namespace="/gateway",
        )

    async def on_guild_role_create(self, role):
        await self.io.emit(
            "GUILD_ROLE_CREATE",
            data=get_formatted_role(role),
            room=str("GUILD_" + str(role.guild.id)),
            namespace="/gateway",
        )

    async def on_guild_role_update(self, role):
        await self.io.emit(
            "GUILD_ROLE_UPDATE",
            data=get_formatted_role(role),
            room=str("GUILD_" + str(role.guild.id)),
            namespace="/gateway",
        )

    async def on_guild_role_delete(self, role):
        await self.io.emit(
            "GUILD_ROLE_DELETE",
            data=get_formatted_role(role),
            room=str("GUILD_" + str(role.guild.id)),
            namespace="/gateway",
        )
