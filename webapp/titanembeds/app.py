import time
import random
import logging
import datetime
from datetime import timedelta

from config import config
from werkzeug.middleware.proxy_fix import ProxyFix

try:
    import uwsgi
    from gevent import monkey

    monkey.patch_all()
except:
    if config.get("websockets-mode", None) == "eventlet":
        import eventlet

        eventlet.monkey_patch()
    elif config.get("websockets-mode", None) == "gevent":
        from gevent import monkey

        monkey.patch_all()

import titanembeds.constants as constants
from flask import Flask, render_template, request, session
from flask_sslify import SSLify
from titanembeds.database import (
    get_administrators_list,
    get_application_settings,
    init_application_settings,
)
from titanembeds.utils import (  # , sentry
    babel,
    discord_api,
    language_code_list,
    rate_limiter,
    socketio,
)

from .blueprints import admin, api, embed, gateway, user
from .database import db
from .redisqueue import redis_store


class Error(Exception):
    pass


class ConfigError(Error):
    pass


app_start_stamp = time.time()

app = Flask(__name__, static_folder="static")

if __name__ != "__main__":
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

app.config["SQLALCHEMY_DATABASE_URI"] = config["database-uri"]
# Suppress the warning/no need this on for now.
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["RATELIMIT_HEADERS_ENABLED"] = True
app.config["SQLALCHEMY_POOL_RECYCLE"] = 100
app.config["SQLALCHEMY_POOL_SIZE"] = 500
app.config["SQLALCHEMY_MAX_OVERFLOW"] = -1
app.config["RATELIMIT_STORAGE_URL"] = config["redis-uri"]
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=3)
app.config["REDIS_URL"] = config["redis-uri"]
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024  # Limit upload size to 4mb
if not config.get("disable-samesite-cookie-flag", False):
    app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.secret_key = config["app-secret"]

# sentry.init_app(app)
db.init_app(app)

rate_limiter.init_app(app)

if config["enable-ssl"] and config["https-proxy"]:
    raise ConfigError("Cannot set both `enable-ssl` and `https-proxy`")
if config["enable-ssl"]:
    sslify = SSLify(app, permanent=True)
if config["https-proxy"]:
    app.wsgi_app = ProxyFix(app.wsgi_app)


socketio.init_app(
    app,
    message_queue=config["redis-uri"],
    path="gateway",
    async_mode=config.get("websockets-mode", None),
)
babel.init_app(app)
redis_store.init_app(app)

app.register_blueprint(api.api, url_prefix="/api", template_folder="/templates")
app.register_blueprint(admin.admin, url_prefix="/admin", template_folder="/templates")
app.register_blueprint(user.user, url_prefix="/user", template_folder="/templates")
app.register_blueprint(embed.embed, url_prefix="/embed", template_folder="/templates")
socketio.on_namespace(gateway.Gateway("/gateway"))


@babel.localeselector
def get_locale():
    param_lang = request.args.get("lang", None)
    if param_lang in language_code_list():
        return param_lang
    return request.accept_languages.best_match(language_code_list())


@app.route("/")
def index():
    return render_template("index.html.j2")


@app.route("/about")
def about():
    return render_template("about.html.j2")


@app.route("/terms")
def terms():
    return render_template("terms_and_conditions.html.j2")


@app.route("/privacy")
def privacy():
    return render_template("privacy_policy.html.j2")


@app.route("/vote")
def vote():
    return render_template(
        "discordbotsorg_vote.html.j2", referrer=request.args.get("referrer", None)
    )


@app.route("/global_banned_words")
def global_banned_words():
    return render_template("global_banned_words.html.j2")


@app.before_first_request
def before_first_request():
    init_application_settings()
    discord_api.init_discordrest()


@app.context_processor
def context_processor():
    return {
        "random": random,
        "application_settings": get_application_settings(),
        "devs": get_administrators_list(),
        "sentry_js_dsn": config.get("sentry-js-dsn", None),
        "constants": constants,
        "af_mode_enabled": datetime.datetime.now().date()
        == datetime.date(datetime.datetime.now().year, 4, 1),
        "dbl_voted": session.get("unauthenticated", True) == False
        and bool(redis_store.get("DiscordBotsOrgVoted/" + str(session.get("user_id", -1)))),
        "app_start_stamp": app_start_stamp,
    }


# @app.errorhandler(500)
# def internal_server_error(error):
#     return render_template('500.html.j2',
#         event_id=g.sentry_event_id,
#         public_dsn=sentry.client.get_public_dsn('https')
#     ), 500
