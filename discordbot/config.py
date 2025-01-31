import re
from os import environ as env

from dotenv import load_dotenv

load_dotenv()

config = {
    "database-uri": re.sub(
        "^postgres:",
        "postgresql:",
        env.get(
            "DATABASE_URL", "postgresql://titan:titan@localhost:5432/titan"
        ),
    ),
    "redis-uri": env.get("REDIS_URL", "redis://"),
    "titan-web-url": "https://ddr-titan.fly.dev/",
    "bot-token": env["TITAN_BOT_TOKEN"],
    "titan-web-app-secret": env["TITAN_WEBAPP_SECRET"],
    "discord-bots-org-token": env.get("DISCORDBOTS_POST_STATS_TOKEN"),
    "bots-discord-pw-token": env.get("BOTS.DISCORD.PW_POST_STATS_TOKEN"),
    "sentry-dsn": env.get("TITAN_WEBAPP_SENTRY_DSN", ""),
    "bot-http-port": env.get("TITAN_BOT_PORT", 8080),
    "bot-http-listen-interfaces": env.get(
        "TITAN_BOT_HTTP_LISTEN_INTERFACES", "127.0.0.1"
    ),
}
