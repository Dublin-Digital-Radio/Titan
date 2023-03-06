import random
import string
import hashlib

from config import config
from flask import request, session


def get_client_ipaddr():
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip = request.remote_addr

    return hashlib.sha512(
        (config["app-secret"] + ip).encode("utf-8")
    ).hexdigest()[:15]


def generate_session_key():
    sess = session.get("sessionunique", None)
    if not sess:
        rand_str = lambda n: "".join(
            [random.choice(string.ascii_lowercase) for i in range(n)]
        )
        session["sessionunique"] = rand_str(25)
        sess = session["sessionunique"]
    return sess  # Totally unique


def make_cache_key(*args, **kwargs):
    path = request.path
    args = str(hash(frozenset(request.args.items())))
    ip = get_client_ipaddr()
    sess = generate_session_key()
    return path + args + sess + ip


def make_user_cache_key(*args, **kwargs):
    ip = get_client_ipaddr()
    sess = generate_session_key()
    return sess + ip


def make_guilds_cache_key():
    sess = generate_session_key()
    ip = get_client_ipaddr()
    return sess + ip + "user_guilds"


def make_guildchannels_cache_key():
    guild_id = request.values.get("guild_id", "0")
    sess = generate_session_key()
    ip = get_client_ipaddr()
    return sess + ip + guild_id + "user_guild_channels"


def channel_ratelimit_key():  # Generate a bucket with given channel & unique session key
    sess = generate_session_key()
    channel_id = request.values.get("channel_id", "0")
    return sess + channel_id


def guild_ratelimit_key():
    ip = get_client_ipaddr()
    guild_id = request.values.get("guild_id", "0")
    return ip + guild_id
