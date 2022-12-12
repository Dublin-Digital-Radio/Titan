import json
from pprint import pformat

from flask import abort, request, session
from flask_socketio import disconnect
from oauthlib.oauth2 import InvalidGrantError
from titanembeds import redis_cache
from titanembeds.cache_keys import make_user_cache_key
from titanembeds.discord_rest.oauth import (
    PERMISSION_BAN,
    PERMISSION_KICK,
    PERMISSION_MANAGE,
    log,
    make_authenticated_session,
)


def discordrest_from_user(endpoint):
    discord = make_authenticated_session(token=session["user_keys"])
    try:
        return discord.get(f"https://discordapp.com/api/v6{endpoint}")
    except InvalidGrantError as ex:
        log.exception("Invalid grant")
        abort(401)


def get_current_authenticated_user():
    req = discordrest_from_user("/users/@me")
    if req.status_code != 200:
        abort(req.status_code)

    return req.json()


def user_has_permission(permission, index):
    return bool((int(permission) >> index) & 1)


def get_user_guilds():
    cache_key = f"OAUTH/USERGUILDS/{make_user_cache_key()}"

    cache = redis_cache.redis_store.get(cache_key)
    if cache:
        log.debug(
            "got user guilds from cache: '%s'", pformat(json.loads(cache))
        )
        return json.loads(cache)

    req = discordrest_from_user("/users/@me/guilds")
    if req.status_code != 200:
        log.info("could not authenticate user with discord")
        if hasattr(request, "sid"):
            disconnect()
            return
        abort(req.status_code)

    result = req.json()
    redis_cache.redis_store.set(cache_key, json.dumps(result), 250)

    log.debug(
        "get_user_guilds - type '%s' - value: '%s'",
        type(result),
        pformat(result),
    )
    return result


def get_user_managed_servers():
    guilds = get_user_guilds() or []

    filtered = []
    for guild in guilds:
        permission = guild[
            "permissions"
        ]  # Manage Server, Ban Members, Kick Members
        if (
            guild["owner"]
            or user_has_permission(permission, PERMISSION_MANAGE)
            or user_has_permission(permission, PERMISSION_BAN)
            or user_has_permission(permission, PERMISSION_KICK)
        ):
            filtered.append(guild)

    return sorted(filtered, key=lambda g: g["name"])


def check_user_can_administrate_guild(guild_id):
    return guild_id in [guild["id"] for guild in get_user_managed_servers()]


def check_user_permission(guild_id, permission_id):
    for guild in get_user_managed_servers():
        if guild["id"] == guild_id:
            return (
                user_has_permission(guild["permissions"], permission_id)
                or guild["owner"]
            )

    return False
