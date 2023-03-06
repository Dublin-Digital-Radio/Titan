import sys
import json
import time

import requests
from config import config
from titanembeds import redisqueue

_DISCORD_API_BASE = "https://discordapp.com/api/v6"


def json_or_text(response):
    if response.headers["content-type"] == "application/json":
        return response.json()

    return response.text


class DiscordREST:
    def __init__(self, bot_token):
        self.global_redis_prefix = "discordapiratelimit/"
        self.bot_token = bot_token
        self.user_agent = f"TitanEmbeds (https://github.com/TitanEmbeds/Titan) Python/{sys.version_info} requests/{requests.__version__}"

    def init_discordrest(self):
        if not self._bucket_contains("global_limited"):
            self._set_bucket("global_limited", "False")
            self._set_bucket("global_limit_expire", 0)

    def _get_bucket(self, key):
        value = redisqueue.redis_store.get(self.global_redis_prefix + key)
        if value:
            value = value
        return value

    def _set_bucket(self, key, value):
        return redisqueue.redis_store.set(self.global_redis_prefix + key, value)

    def _bucket_contains(self, key):
        return redisqueue.redis_store.exists(self.global_redis_prefix + key)

    def request(self, verb, url, **kwargs):
        headers = {
            "User-Agent": self.user_agent,
            "Authorization": f"Bot {self.bot_token}",
        }
        params = None
        if "params" in kwargs:
            params = kwargs["params"]

        data = None
        if "data" in kwargs:
            data = kwargs["data"]
        if "json" in kwargs and kwargs["json"] != False:
            headers["Content-Type"] = "application/json"
            data = json.dumps(data)

        for tries in range(5):
            curepoch = time.time()
            if self._get_bucket("global_limited") == "True":
                time.sleep(
                    int(float(self._get_bucket("global_limit_expire")))
                    - curepoch
                )
                curepoch = time.time()

            if (
                self._bucket_contains(url)
                and float(int(self._get_bucket(url))) > curepoch
            ):
                time.sleep(int(self._get_bucket(url)) - curepoch)

            url_formatted = _DISCORD_API_BASE + url
            if data and "payload_json" in data:
                if "Content-Type" in headers:
                    del headers["Content-Type"]
                req = requests.request(
                    verb,
                    url_formatted,
                    params=params,
                    files=data,
                    headers=headers,
                )
            else:
                req = requests.request(
                    verb,
                    url_formatted,
                    params=params,
                    data=data,
                    headers=headers,
                )

            if "X-RateLimit-Remaining" in req.headers:
                remaining = req.headers["X-RateLimit-Remaining"]
                if remaining == "0" and req.status_code != 429:
                    self._set_bucket(url, int(req.headers["X-RateLimit-Reset"]))

            if 300 > req.status_code >= 200:
                self._set_bucket("global_limited", "False")
                return {
                    "success": True,
                    "content": json_or_text(req),
                    "code": req.status_code,
                }

            if req.status_code == 429:
                if "X-RateLimit-Global" not in req.headers:
                    self._set_bucket(url, int(req.headers["X-RateLimit-Reset"]))
                else:
                    self._set_bucket("global_limited", "True")
                    self._set_bucket(
                        "global_limit_expire",
                        time.time() + int(req.headers["Retry-After"]),
                    )

            if req.status_code == 502 and tries <= 5:
                time.sleep(1 + tries * 2)
                continue

            if req.status_code == 403 or req.status_code == 404:
                return {
                    "success": False,
                    "content": json_or_text(req),
                    "code": req.status_code,
                }

        return {
            "success": False,
            "code": req.status_code,
            "content": json_or_text(req),
        }

    #####################
    # Channel
    #####################

    def create_message(self, channel_id, content, file=None, richembed=None):
        _endpoint = f"/channels/{channel_id}/messages"
        payload = {"content": content}
        is_json = False

        if file:
            payload = {
                "payload_json": (None, json.dumps(payload)),
                "file": (
                    file.filename,
                    file.read(),
                    "application/octet-stream",
                ),
            }

        if richembed:
            if richembed.get("type"):
                del richembed["type"]
            payload["embed"] = richembed
            if not content:
                del payload["content"]
            is_json = True

        return self.request("POST", _endpoint, data=payload, json=is_json)

    #####################
    # Guild
    #####################

    def add_guild_member(self, guild_id, user_id, access_token, **kwargs):
        _endpoint = f"/guilds/{guild_id}/members/{user_id}"
        payload = {"access_token": access_token}
        payload.update(kwargs)
        return self.request("PUT", _endpoint, data=payload, json=True)

    def get_guild_embed(self, guild_id):
        _endpoint = f"/guilds/{guild_id}/embed"
        r = self.request("GET", _endpoint)
        return r

    def get_guild_member(self, guild_id, user_id):
        _endpoint = f"/guilds/{guild_id}/members/{user_id}"
        return self.request("GET", _endpoint)

    def modify_guild_embed(self, guild_id, **kwargs):
        _endpoint = f"/guilds/{guild_id}/embed"
        return self.request("PATCH", _endpoint, data=kwargs, json=True)

    #####################
    # Widget Handler
    #####################

    def get_widget(self, guild_id):
        _endpoint = f"{_DISCORD_API_BASE}/servers/{guild_id}/widget.json"

        embed = self.get_guild_embed(guild_id)
        if not embed.get("success", True):
            return {"success": False}

        if not embed["content"]["enabled"]:
            self.modify_guild_embed(guild_id, enabled=True, channel_id=guild_id)

        return requests.get(_endpoint).json()

    #####################
    # Webhook
    #####################

    def create_webhook(self, guild_id, channel_id, name, avatar=None):
        _endpoint = f"/channels/{channel_id}/webhooks"
        payload = {"name": name}
        if avatar:
            payload["avatar"] = avatar
        redisqueue.guild_clear_cache(guild_id)
        return self.request("POST", _endpoint, data=payload, json=True)

    def execute_webhook(
        self,
        webhook_id,
        webhook_token,
        username,
        avatar,
        content,
        file=None,
        richembed=None,
        wait=True,
    ):
        _endpoint = f"/webhooks/{webhook_id}/{webhook_token}"
        if wait:
            _endpoint += "?wait=true"

        payload = {
            "content": content,
            "avatar_url": avatar,
            "username": username,
        }
        if file:
            payload = {
                "payload_json": (None, json.dumps(payload)),
                "file": (
                    file.filename,
                    file.read(),
                    "application/octet-stream",
                ),
            }

        is_json = False
        if richembed:
            if richembed.get("type"):
                del richembed["type"]

            payload["embeds"] = [richembed]
            if not content:
                del payload["content"]
            if not file:
                is_json = True

        return self.request("POST", _endpoint, data=payload, json=is_json)

    def delete_webhook(self, webhook_id, webhook_token, guild_id):
        redisqueue.guild_clear_cache(guild_id)
        _endpoint = f"/webhooks/{webhook_id}/{webhook_token}"
        return self.request("DELETE", _endpoint)


discord_api = DiscordREST(config["bot-token"])
