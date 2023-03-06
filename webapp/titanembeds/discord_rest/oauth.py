import logging

from config import config
from flask import request, session, url_for
from requests_oauthlib import OAuth2Session

log = logging.getLogger(__name__)
BOT_PERMISSIONS = 641195117
PERMISSION_MANAGE = 5
PERMISSION_BAN = 2
PERMISSION_KICK = 1
AUTHORIZE_URL = "https://discordapp.com/api/oauth2/authorize"
TOKEN_URL = "https://discordapp.com/api/oauth2/token"
AVATAR_BASE_URL = "https://cdn.discordapp.com/avatars/"
GUILD_ICON_URL = "https://cdn.discordapp.com/icons/"


def make_authenticated_session(token=None, state=None, scope=None):
    def update_user_token(discord_token):
        session["user_keys"] = discord_token

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
        auto_refresh_url=TOKEN_URL,
        token_updater=update_user_token,
    )


def get_token(state):
    discord = make_authenticated_session(state=state)
    return discord.fetch_token(
        TOKEN_URL,
        client_secret=config["client-secret"],
        authorization_response=request.url,
    )


def get_authorization_url(scope):
    discord = make_authenticated_session(scope=scope)
    # authorization_url, state
    return discord.authorization_url(
        AUTHORIZE_URL, access_type="offline", prompt="none"
    )
