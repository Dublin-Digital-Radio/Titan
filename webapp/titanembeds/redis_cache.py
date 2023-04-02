from redis import Redis

redis_store = Redis()


def init_redis(url):
    global redis_store
    redis_store = Redis.from_url(url, decode_responses=True)


def bump_user_presence_timestamp(guild_id, user_type, client_key):
    redis_key = f"MemberPresence/{guild_id}/{user_type}/{client_key}"
    redis_store.set(redis_key, "", 60)


def get_online_embed_user_keys(guild_id="*", user_type=None):
    user_type = (
        [user_type]
        if user_type
        else ["AuthenticatedUsers", "UnauthenticatedUsers"]
    )

    return {
        utype: [
            k.split("/")[-1]
            for k in redis_store.keys(f"MemberPresence/{guild_id}/{utype}/*")
        ]
        for utype in user_type
    }


def guild_clear_cache(guild_id):
    key = f"Queue/guilds/{guild_id}"
    redis_store.delete(key)
