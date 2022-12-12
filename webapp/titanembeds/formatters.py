from email import utils as emailutils

from discord import Role
from discord.channel import CategoryChannel, TextChannel


def format_datetime(datetimeobj):
    # https://stackoverflow.com/questions/3453177/convert-python-datetime-to-rfc-2822
    return emailutils.format_datetime(datetimeobj)


def format_message(message):
    edit_ts = message.edited_at
    edit_ts = None if not edit_ts else format_datetime(edit_ts)

    msg_type = (
        int(message.type) if isinstance(message.type, int) else message.type.value
    )

    msg = {
        "id": str(message.id),
        "channel_id": str(message.channel.id),
        "content": message.content,
        "author": format_message_author(message),
        "timestamp": format_datetime(message.created_at),
        "edited_timestamp": edit_ts,
        "type": msg_type,
    }

    if hasattr(message, "mentions"):
        msg["mentions"] = format_message_mentions(message.mentions)
    if hasattr(message, "attachments"):
        msg["attachments"] = format_attachments_list(message.attachments)
    if hasattr(message, "embeds"):
        msg["embeds"] = format_embeds_list(message.embeds)
    if hasattr(message, "author"):
        msg["author"]["nickname"] = None
        if hasattr(message.author, "nick") and message.author.nick:
            msg["author"]["nickname"] = message.author.nick
    if hasattr(message, "mentions"):
        for mention in msg["mentions"]:
            mention["nickname"] = None
            if member := message.guild.get_member(mention["id"]):
                mention["nickname"] = member.nick
    if hasattr(message, "reactions"):
        msg["reactions"] = format_message_reactions(message.reactions)

    return msg


def format_user(user):
    userobj = {
        "avatar": user.avatar.key if user.avatar else None,
        "avatar_url": str(user.avatar.replace(static_format="png", size=512))
        if user.avatar
        else "",
        "color": str(user.color)[1:],
        "discriminator": user.discriminator,
        "game": None,
        "hoist-role": None,
        "id": str(user.id),
        "status": str(user.status),
        "username": user.name,
        "nick": None,
        "bot": user.bot,
        "roles": [],
    }
    if userobj["color"] == "000000":
        userobj["color"] = None
    # if userobj["avatar_url"][len(userobj["avatar_url"])-15:] != ".jpg":
    #     userobj["avatar_url"] = userobj["avatar_url"][:len(userobj["avatar_url"])-14] + ".jpg"

    if user.nick:
        userobj["nick"] = user.nick
    if getattr(user, "activity", None):
        userobj["activity"] = {"name": user.activity.name}

    for role in sorted(user.roles, key=lambda k: k.position, reverse=True):
        userobj["roles"].append(str(role.id))
        if role.hoist and userobj["hoist-role"] is None:
            userobj["hoist-role"] = {
                "id": str(role.id),
                "name": role.name,
                "position": role.position,
            }

    return userobj


def format_message_author(message):
    if not hasattr(message, "author"):
        return {}

    return {
        "username": message.author.name,
        "discriminator": message.author.discriminator,
        "bot": message.author.bot,
        "id": str(message.author.id),
        "avatar": message.author.avatar.key
        if message.author and message.author.avatar
        else None,
    }


def format_formatted_emojis(emojis):
    return [
        {
            "id": str(emo.id),
            "managed": emo.managed,
            "name": emo.name,
            "require_colons": emo.require_colons,
            "roles": format_roles_list(emo.roles),
            "url": str(emo.url),
        }
        for emo in emojis
    ]


def format_guild(guild, webhooks=None):
    return {
        "id": str(guild.id),
        "name": guild.name,
        "icon": guild.icon.key if guild.icon else None,
        "icon_url": str(guild.icon),
        "owner_id": guild.owner_id,
        "roles": format_roles_list(guild.roles),
        "channels": format_channels_list(guild.channels),
        "webhooks": format_webhooks_list(webhooks or []),
        "emojis": format_emojis_list(guild.emojis),
    }


def format_channel(channel):
    return {
        "id": str(channel.id),
        "guild_id": str(channel.guild.id),
    }


def format_role(role):
    return {
        "id": str(role.id),
        "guild_id": str(role.guild.id),
        "name": role.name,
        "color": role.color.value,
        "hoist": role.hoist,
        "position": role.position,
        "permissions": role.permissions.value,
    }


def format_message_mentions(mentions):
    return [
        {
            "username": author.name,
            "discriminator": author.discriminator,
            "bot": author.bot,
            "id": str(author.id),
            "avatar": author.avatar.key if author.avatar else None,
        }
        for author in mentions
    ]


def format_webhooks_list(guild_webhooks):
    return [
        {
            "id": str(webhook.id),
            "guild_id": str(webhook.guild.id),
            "channel_id": str(webhook.channel.id),
            "name": webhook.name,
            "token": webhook.token,
        }
        for webhook in guild_webhooks
        if webhook.channel and webhook.guild
    ]


def format_emojis_list(guildemojis):
    return [
        {
            "id": str(emote.id),
            "name": emote.name,
            "require_colons": emote.require_colons,
            "managed": emote.managed,
            "roles": [str(role.id) for role in emote.roles],
            "url": str(emote.url),
            "animated": emote.animated,
        }
        for emote in guildemojis
    ]


def format_roles_list(guildroles):
    return [
        {
            "id": str(role.id),
            "name": role.name,
            "color": role.color.value,
            "hoist": role.hoist,
            "position": role.position,
            "permissions": role.permissions.value,
        }
        for role in guildroles
    ]


def format_channels_list(guildchannels):
    channels = []
    for channel in guildchannels:
        if not (
            isinstance(channel, TextChannel) or isinstance(channel, CategoryChannel)
        ):
            continue

        overwrites = []
        for target, overwrite in channel.overwrites.items():
            if not target:
                continue

            allow, deny = overwrite.pair()
            overwrites.append(
                {
                    "id": str(target.id),
                    "type": "role" if isinstance(target, Role) else "member",
                    "allow": allow.value,
                    "deny": deny.value,
                }
            )

        is_text_channel = isinstance(channel, TextChannel)
        channels.append(
            {
                "id": str(channel.id),
                "name": channel.name,
                "topic": channel.topic if is_text_channel else None,
                "position": channel.position,
                "type": "text" if is_text_channel else "category",
                "permission_overwrites": overwrites,
                "parent_id": str(channel.category.id) if channel.category else None,
                "nsfw": channel.is_nsfw(),
            }
        )
    return channels


def format_attachments_list(attachments):
    attr = []
    for attach in attachments:
        a = {
            "id": str(attach.id),
            "size": attach.size,
            "filename": attach.filename,
            "url": attach.url,
            "proxy_url": attach.proxy_url,
        }
        if attach.height:
            a["height"] = attach.height
        if attach.width:
            a["width"] = attach.width
        attr.append(a)
    return attr


def format_embeds_list(embeds):
    return [e.to_dict() for e in embeds]


def format_message_reactions(reactions):
    return [
        {"emoji": get_partial_emoji(reaction.emoji), "count": reaction.count}
        for reaction in reactions
    ]


def get_partial_emoji(emoji):
    if isinstance(emoji, str):
        return {"animated": False, "id": None, "name": str(emoji)}

    return {
        "animated": emoji.animated,
        "id": str(emoji.id),
        "name": emoji.name,
    }
