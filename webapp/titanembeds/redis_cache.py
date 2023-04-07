from redis.asyncio import Redis

redis_store = Redis()


async def init_redis(url):
    global redis_store
    redis_store = await Redis.from_url(url, decode_responses=True)


async def bump_user_presence_timestamp(guild_id, user_type, client_key):
    redis_key = f"MemberPresence/{guild_id}/{user_type}/{client_key}"
    await redis_store.set(redis_key, "", 60)


async def get_online_embed_user_keys(guild_id="*", user_type=None):
    user_type = (
        [user_type]
        if user_type
        else ["AuthenticatedUsers", "UnauthenticatedUsers"]
    )

    return {
        utype: [
            k.split("/")[-1]
            for k in await redis_store.keys(
                f"MemberPresence/{guild_id}/{utype}/*"
            )
        ]
        for utype in user_type
    }


async def guild_clear_cache(guild_id):
    key = f"Queue/guilds/{guild_id}"
    await redis_store.delete(key)
