import logging
from abc import abstractmethod

import aiohttp

log = logging.getLogger(__name__)


class DiscordBots:
    def __init__(self, client_id, token):
        self.url = self.base_url.format(client_id)
        self.token = token

    @property
    @abstractmethod
    def base_url(self):
        pass

    async def post(self, count, shard_count, shard_id):
        if not self.token:
            log.info(
                f"{self.__class__} cannot post stats because `token` is not defined"
            )
            return

        headers = {"Authorization": self.token}
        payload = {
            "server_count": count,
            "shard_count": shard_count,
            "shard_id": shard_id,
        }
        async with aiohttp.ClientSession() as aioclient:
            await aioclient.post(self.url, json=payload, headers=headers)


class DiscordBotsOrg(DiscordBots):  # https://discordbots.org
    base_url = "https://discordbots.org/api/bots/{}/stats"


class BotsDiscordPw(DiscordBots):  # https://bots.discord.pw/
    base_url = "https://bots.discord.pw/api/bots/{}/stats"
