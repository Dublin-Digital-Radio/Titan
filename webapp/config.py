import re
from os import environ as env

from dotenv import load_dotenv

load_dotenv()

config = {
    "debug": env.get("TITAN_WEBAPP_DEBUG", False),
    "app-secret": env["TITAN_APP_SECRET"],
    "database-uri": re.sub(
        "^postgres:",
        "postgresql:",
        env.get(
            "DATABASE_URL", "postgresql://titan:titan@localhost:5432/titan"
        ),
    ),
    "redis-uri": env.get("REDIS_URL", "redis://"),
    # Create an app over here https://discordapp.com/developers/applications/me
    # and fill these fields out
    "client-id": env["DISCORD_CLIENT_ID"],
    "client-secret": env["DISCORD_CLIENT_SECRET"],
    "bot-token": env["DISCORD_BOT_TOKEN"],
    "bot-http-port": env.get("TITAN_BOT_PORT", 8080),
    "bot-http-url": env.get("TITAN_BOT_ADDR", "localhost"),
    "bot-http-over-ipv6": env.get("TITAN_BOT_IPV6", False),
    # are we running behind a proxy which terminates TLS - cannot be used with `enable-ssl`
    "https-proxy": env.get("TITAN_HTTPS_PROXY", False),
    # redirect all http to https - cannot be used with `https-proxy`
    "enable-ssl": env.get("TITAN_ENABLE_SSL", False),
    #
    "engineio-logging": True,
    # https://titanembeds.com/api/webhook/discordbotsorg/vote
    # Secret code used in the authorization header for DBL webhook
    "discordbotsorg-webhook-secret": env.get("DISCORDBOTSORG_WEBHOOK_SECRET"),
    # Sentry.io is used to track and upload errors
    "sentry-dsn": "",  # Copy the dns string when creating a project on sentry
    # Same as above, but you can create a seperate sentry project to track the
    # client side js errors
    "sentry-js-dsn": "",
    # Rest API in https://developer.paypal.com/developer/applications
    "paypal-client-id": env.get("PAYPAL_CLIENT_ID"),
    "paypal-client-secret": env.get("PAYPAL_CLIENT_SECRET"),
    # V2 reCAPTCHA from https://www.google.com/recaptcha/admin
    "recaptcha-site-key": env.get("RECAPTCHA_V2_SITE_KEY"),
    "recaptcha-secret-key": env.get("RECAPTCHA_V2_SECRET_KEY"),
    # Patreon from https://www.patreon.com/portal
    "patreon-client-id": "",
    "patreon-client-secret": "",
    # "" or "eventlet"
    "git-commit": env.get("GIT_COMMIT"),
    "enable-code-highlighting": env.get(
        "TITAN_WEBAPP_ENABLE_CODE_HIGHLIGHTING", False
    ),
    "cdn-domain": env.get("TITAN_CDN_DOMAIN"),
}
