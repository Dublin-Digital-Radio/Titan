import logging as _logging

import aiohttp as _aiohttp
import discord as _discord
from config import config as _config

__all__ = ["ban", "unban", "kick", "invite", "server", "help", "members"]

log = _logging.getLogger(__name__)


async def ban(message):
    if not message.author.guild_permissions.ban_members:
        await message.channel.send(
            message.author.mention
            + " I'm sorry, but you do not have permissions to ban guest members."
        )
        return

    content = message.content.strip().split()
    if len(content) == 2:
        await message.channel.send(
            message.author.mention
            + " Please provide a username-query (or optionally a discriminator) to ban a guest user.\nExample: `ban Titan#0001`"
        )
        return

    username = (
        content[2][: content[2].find("#")] if "#" in content[2] else content[2]
    )
    discriminator = (
        int(content[2][content[2].find("#") + 1 :])
        if "#" in content[2]
        else None
    )
    headers = {"Authorization": _config["titan-web-app-secret"]}
    payload = {
        "guild_id": message.guild.id,
        "placer_id": message.author.id,
        "username": username,
    }

    if discriminator:
        payload["discriminator"] = discriminator
    url = _config["titan-web-url"] + "api/bot/ban"

    async with _aiohttp.ClientSession() as aioclient:
        async with aioclient.post(url, json=payload, headers=headers) as resp:
            j = await resp.json()
            if "error" in j:
                await message.channel.send(
                    f"{message.author.mention} Ban error! {j['error']}"
                )
                return
            if "success" in j:
                await message.channel.send(
                    f'{message.author.mention} {j["success"]}'
                )
                return

    await message.channel.send(
        "Unhandled webservice error in banning guest user!"
    )


async def unban(message):
    if not message.author.guild_permissions.ban_members:
        await message.channel.send(
            message.author.mention
            + " I'm sorry, but you do not have permissions to unban guest members."
        )
        return

    content = message.content.strip().split()
    if len(content) == 2:
        await message.channel.send(
            message.author.mention
            + " Please provide a username-query (or optionally a discriminator) to unban a guest user.\nExample: `unban Titan#0001`"
        )
        return

    username = (
        content[2][: content[2].find("#")] if "#" in content[2] else content[2]
    )
    discriminator = (
        int(content[2][content[2].find("#") + 1 :])
        if "#" in content[2]
        else None
    )
    headers = {"Authorization": _config["titan-web-app-secret"]}
    payload = {
        "guild_id": message.guild.id,
        "lifter_id": message.author.id,
        "username": username,
    }

    if discriminator:
        payload["discriminator"] = discriminator
    url = _config["titan-web-url"] + "api/bot/unban"

    async with _aiohttp.ClientSession() as aioclient:
        async with aioclient.post(url, json=payload, headers=headers) as resp:
            j = await resp.json()
            if "error" in j:
                await message.channel.send(
                    f"{message.author.mention} Unban error! {j['error']}"
                )
                return
            if "success" in j:
                await message.channel.send(
                    f"{message.author.mention} {j['success']}"
                )
                return

    await message.channel.send(
        "Unhandled webservice error in unbanning guest user!"
    )


async def kick(message):
    if not message.author.guild_permissions.kick_members:
        await message.channel.send(
            message.author.mention
            + " I'm sorry, but you do not have permissions to kick guest members."
        )
        return

    content = message.content.strip().split()
    if len(content) == 2:
        await message.channel.send(
            message.author.mention
            + " Please provide a username-query (or optionally a discriminator) to kick a guest user.\nExample: `kick Titan#0001`"
        )
        return

    username = (
        content[2][: content[2].find("#")] if "#" in content[2] else content[2]
    )
    discriminator = (
        int(content[2][content[2].find("#") + 1 :])
        if "#" in content[2]
        else None
    )
    headers = {"Authorization": _config["titan-web-app-secret"]}
    payload = {"guild_id": message.guild.id, "username": username}
    if discriminator:
        payload["discriminator"] = discriminator
    url = _config["titan-web-url"] + "api/bot/revoke"

    async with _aiohttp.ClientSession() as aioclient:
        async with aioclient.post(url, json=payload, headers=headers) as resp:
            j = await resp.json()
            if "error" in j:
                await message.channel.send(
                    f"{message.author.mention} Kick error! {j['error']}"
                )
                return
            if "success" in j:
                await message.channel.send(
                    f"{message.author.mention} {j['success']}"
                )
                return

    await message.channel.send(
        "Unhandled webservice error in kicking guest user!"
    )


async def invite(message):
    await message.channel.send(
        "You can invite Titan to your server by visiting this link: https://discordapp.com/oauth2/authorize?&client_id=299403260031139840&scope=bot&permissions=641195117"
    )


async def server(message):
    await message.channel.send(
        "Join the Titan Embeds Discord server! https://discord.gg/pFDDtcN"
    )


async def help(message):
    await message.channel.send(
        "Commands available on: https://docs.titanembeds.com/Commands/\nTo setup an embed please visit: https://titanembeds.com/user/dashboard"
    )


async def members(message):
    headers = {"Authorization": _config["titan-web-app-secret"]}
    payload = {
        "guild_id": message.guild.id,
    }
    users = {"authenticated": [], "unauthenticated": []}
    url = _config["titan-web-url"] + "api/bot/members"

    async with _aiohttp.ClientSession() as aioclient:
        async with aioclient.get(url, params=payload, headers=headers) as resp:
            if 200 <= resp.status < 300:
                users = await resp.json()
    embed_description = ""

    if users["authenticated"]:
        embed_description = embed_description + "__(Discord)__\n"
        count = 1
        for user in users["authenticated"]:
            server_user = message.guild.get_member(int(user["id"]))

            if not server_user:
                log.error("could not find user with id %s", user["id"])
                continue

            embed_description = (
                embed_description
                + f"**{count}.** {server_user.name}#{server_user.discriminator}"
            )
            if server_user.nick:
                embed_description = embed_description + f" ({server_user.nick})"
            embed_description = embed_description + f" {server_user.mention}\n"
            count = count + 1

    if users["unauthenticated"]:
        if users["authenticated"]:
            embed_description = embed_description + "\n"
        embed_description = embed_description + "__(Guest)__\n"

        count = 1
        for user in users["unauthenticated"]:
            embed_description = (
                embed_description
                + f"**{count}.** {user['username']}#{user['discriminator']}\n"
            )
            count = count + 1

    if users["authenticated"] or users["unauthenticated"]:
        embed_description = embed_description + "\n"

    embed_description = (
        embed_description
        + f"**Total Members Online: __{len(users['authenticated']) + len(users['unauthenticated'])}__**"
    )

    embed = _discord.Embed(
        title="Currently Online Embed Members",
        url="https://ddr-titan.fly.dev/",
        color=7964363,
        description=embed_description,
    )

    if message.channel.permissions_for(message.guild.me).embed_links:
        await message.channel.send(embed=embed)
    else:
        await message.channel.send(
            "__**Currently Online Embed Members**__\n" + embed_description
        )
