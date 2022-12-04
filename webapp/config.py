from os import environ as env

config = {
    "app-secret": env["TITAN_APP_SECRET"],
    # app-location": "/home/titan/Titan/webapp/",
    "database-uri": env.get("DATABASE_URL", "postgres://titan:titan@localhost:5432/titan"),
    "redis-uri": env.get("REDIS_URL", "redis://"),
    # Create an app over here https://discordapp.com/developers/applications/me
    # and fill these fields out
    "client-id": env["DISCORD_CLIENT_ID"],
    "client-secret": env["DISCORD_CLIENT_SECRET"],
    "bot-token": env["DISCORD_BOT_TOKEN"],
    "websockets-mode": env.get("WEBSOCKETS_MODE", "eventlet"),
    "engineio-logging": False,
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
    "recaptcha-secret-key": "",
    # Patreon from https://www.patreon.com/portal
    "patreon-client-id": "",
    "patreon-client-secret": "",
    # "" or "eventlet"
}
