import json
import logging

from config import config
from flask import abort, request, session, url_for
from flask_socketio import disconnect
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
from requests_oauthlib import OAuth2Session
from titanembeds.redisqueue import redis_store
from titanembeds.utils import make_user_cache_key

log = logging.getLogger(__name__)

BOT_PERMISSIONS = 641195117

authorize_url = "https://discordapp.com/api/oauth2/authorize"
token_url = "https://discordapp.com/api/oauth2/token"
avatar_base_url = "https://cdn.discordapp.com/avatars/"
guild_icon_url = "https://cdn.discordapp.com/icons/"


def update_user_token(discord_token):
    session["user_keys"] = discord_token


def make_authenticated_session(token=None, state=None, scope=None):
    return OAuth2Session(
        client_id=config["client-id"],
        token=token,
        state=state,
        scope=scope,
        redirect_uri=url_for("user.callback", _external=True, _scheme="https"),
        auto_refresh_kwargs={
            "client_id": config["client-id"],
            "client_secret": config["client-secret"],
        },
        auto_refresh_url=token_url,
        token_updater=update_user_token,
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
    cache = redis_store.get("OAUTH/USERGUILDS/" + str(make_user_cache_key()))
    if cache:
        return cache

    req = discordrest_from_user("/users/@me/guilds")
    if req.status_code != 200:
        if hasattr(request, "sid"):
            disconnect()
            return
        abort(req.status_code)

    req = json.dumps(req.json())
    redis_store.set("OAUTH/USERGUILDS/" + str(make_user_cache_key()), req, 250)
    return req


def get_user_managed_servers():
    fetched = get_user_guilds()
    if not fetched:
        return []

    guilds = json.loads(fetched)
    filtered = []
    for guild in guilds:
        permission = guild["permissions"]  # Manage Server, Ban Members, Kick Members
        if (
            guild["owner"]
            or user_has_permission(permission, 5)
            or user_has_permission(permission, 2)
            or user_has_permission(permission, 1)
        ):
            filtered.append(guild)

    filtered = sorted(filtered, key=lambda guild: guild["name"])
    return filtered


def get_user_managed_servers_safe():
    guilds = get_user_managed_servers()
    if guilds:
        return guilds

    return []


def get_user_managed_servers_id():
    return [guild["id"] for guild in get_user_managed_servers_safe()]


def check_user_can_administrate_guild(guild_id):
    return guild_id in get_user_managed_servers_id()


def check_user_permission(guild_id, id):
    guilds = get_user_managed_servers_safe()
    for guild in guilds:
        if guild["id"] == guild_id:
            return user_has_permission(guild["permissions"], id) or guild["owner"]
    return False


def generate_avatar_url(id, av, discrim="0000", allow_animate=False):
    if av:
        suf = "gif" if allow_animate and str(av).startswith("a_") else "png"
        return f"{avatar_base_url}{id}/{av}.{suf}"

    default_av = [0, 1, 2, 3, 4]
    avatar_no = default_av[int(discrim) % len(default_av)]
    return f"https://cdn.discordapp.com/embed/avatars/{avatar_no}.png"


def generate_guild_icon_url(id, hash):
    return f"{guild_icon_url}{id}/{hash}.png"


def generate_bot_invite_url(guild_id):
    return f"https://discordapp.com/oauth2/authorize?&client_id={config['client-id']}&scope=bot&permissions={BOT_PERMISSIONS}&guild_id={guild_id}"
