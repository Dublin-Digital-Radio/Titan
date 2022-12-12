from email import utils as emailutils

from discord import Role
from discord.channel import CategoryChannel, TextChannel


def format_datetime(datetimeobj):
    # https://stackoverflow.com/questions/3453177/convert-python-datetime-to-rfc-2822
    return emailutils.format_datetime(datetimeobj)


def get_formatted_message(message):
    edit_ts = message.edited_at
    edit_ts = None if not edit_ts else format_datetime(edit_ts)

    msg_type = int(message.type) if isinstance(message.type, int) else message.type.value

    msg = {
        "id": str(message.id),
        "channel_id": str(message.channel.id),
        "content": message.content,
        "author": get_message_author(message),
        "timestamp": format_datetime(message.created_at),
        "edited_timestamp": edit_ts,
        "type": msg_type,
    }

    if hasattr(message, "mentions"):
        msg["mentions"] = get_message_mentions(message.mentions)
    if hasattr(message, "attachments"):
        msg["attachments"] = get_attachments_list(message.attachments)
    if hasattr(message, "embeds"):
        msg["embeds"] = get_embeds_list(message.embeds)
    if hasattr(message, "author"):
        nickname = None
        if hasattr(message.author, "nick") and message.author.nick:
            nickname = message.author.nick
        msg["author"]["nickname"] = nickname
    if hasattr(message, "mentions"):
        for mention in msg["mentions"]:
            mention["nickname"] = None
            member = message.guild.get_member(mention["id"])
            if member:
                mention["nickname"] = member.nick
    if hasattr(message, "reactions"):
        msg["reactions"] = get_message_reactions(message.reactions)

    return msg


def get_formatted_user(user):
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
    if hasattr(user, "activity") and user.activity:
        userobj["activity"] = {"name": user.activity.name}

    roles = sorted(user.roles, key=lambda k: k.position, reverse=True)
    for role in roles:
        userobj["roles"].append(str(role.id))
        if role.hoist and userobj["hoist-role"] is None:
            userobj["hoist-role"] = {
                "id": str(role.id),
                "name": role.name,
                "position": role.position,
            }

    return userobj


def get_message_author(message):
    if not hasattr(message, "author"):
        return {}

    return {
        "username": message.author.name,
        "discriminator": message.author.discriminator,
        "bot": message.author.bot,
        "id": str(message.author.id),
        "avatar": message.author.avatar.key if message.author and message.author.avatar else None,
    }


def get_formatted_emojis(emojis):
    emotes = []
    for emo in emojis:
        emotes.append(
            {
                "id": str(emo.id),
                "managed": emo.managed,
                "name": emo.name,
                "require_colons": emo.require_colons,
                "roles": get_roles_list(emo.roles),
                "url": str(emo.url),
            }
        )
    return emotes


def get_formatted_guild(guild, webhooks=None):
    if webhooks is None:
        webhooks = []

    return {
        "id": str(guild.id),
        "name": guild.name,
        "icon": guild.icon.key if guild.icon else None,
        "icon_url": str(guild.icon),
        "owner_id": guild.owner_id,
        "roles": get_roles_list(guild.roles),
        "channels": get_channels_list(guild.channels),
        "webhooks": get_webhooks_list(webhooks),
        "emojis": get_emojis_list(guild.emojis),
    }


def get_formatted_channel(channel):
    return {
        "id": str(channel.id),
        "guild_id": str(channel.guild.id),
    }


def get_formatted_role(role):
    return {
        "id": str(role.id),
        "guild_id": str(role.guild.id),
        "name": role.name,
        "color": role.color.value,
        "hoist": role.hoist,
        "position": role.position,
        "permissions": role.permissions.value,
    }


def get_message_mentions(mentions):
    ments = []
    for author in mentions:
        ments.append(
            {
                "username": author.name,
                "discriminator": author.discriminator,
                "bot": author.bot,
                "id": str(author.id),
                "avatar": author.avatar.key if author.avatar else None,
            }
        )
    return ments


def get_webhooks_list(guild_webhooks):
    webhooks = []
    for webhook in guild_webhooks:
        if not webhook.channel or not webhook.guild:
            continue

        webhooks.append(
            {
                "id": str(webhook.id),
                "guild_id": str(webhook.guild.id),
                "channel_id": str(webhook.channel.id),
                "name": webhook.name,
                "token": webhook.token,
            }
        )

    return webhooks


def get_emojis_list(guildemojis):
    emojis = []

    for emote in guildemojis:
        emojis.append(
            {
                "id": str(emote.id),
                "name": emote.name,
                "require_colons": emote.require_colons,
                "managed": emote.managed,
                "roles": [str(role.id) for role in emote.roles],
                "url": str(emote.url),
                "animated": emote.animated,
            }
        )
    return emojis


def get_roles_list(guildroles):
    roles = []
    for role in guildroles:
        roles.append(
            {
                "id": str(role.id),
                "name": role.name,
                "color": role.color.value,
                "hoist": role.hoist,
                "position": role.position,
                "permissions": role.permissions.value,
            }
        )
    return roles


def get_channels_list(guildchannels):
    channels = []
    for channel in guildchannels:
        if not (isinstance(channel, TextChannel) or isinstance(channel, CategoryChannel)):
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


def get_attachments_list(attachments):
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


def get_embeds_list(embeds):
    return [e.to_dict() for e in embeds]


def get_message_reactions(reactions):
    reacts = []
    for reaction in reactions:
        reacts.append({"emoji": get_partial_emoji(reaction.emoji), "count": reaction.count})
    return reacts


def get_partial_emoji(emoji):
    emote = {"animated": False, "id": None, "name": str(emoji)}
    if isinstance(emoji, str):
        return emote

    emote["animated"] = emoji.animated
    emote["id"] = str(emoji.id)
    emote["name"] = emoji.name

    return emote
