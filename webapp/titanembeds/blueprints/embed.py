import copy
import json
import time
import random
import logging
from urllib.parse import urlparse

import sqlalchemy.exc
from config import config
from flask import (
    Blueprint,
    abort,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_babel import gettext
from titanembeds import bot_http_client
from titanembeds.database import Guilds, UserCSS, db, list_disabled_guilds
from titanembeds.redis_cache import get_online_embed_user_keys
from titanembeds.utils import (
    generate_guild_icon_url,
    guild_accepts_visitors,
    guild_query_unauth_users_bool,
    guild_unauthcaptcha_enabled,
    int_or_none,
    serializer,
)

log = logging.getLogger(__name__)

embed = Blueprint("embed", __name__)


def get_logingreeting():
    greetings = [
        gettext(
            "Let's get to know each other! My name is Titan, what's yours?"
        ),
        gettext("Hello and welcome!"),
        gettext("What brings you here today?"),
        gettext("....what do you expect this text to say?"),
        gettext("Aha! ..made you look!"),
        gettext("Initiating launch sequence..."),
        gettext("Captain, what's your option?"),
        gettext("Alright, here's the usual~"),
    ]
    return random.choice(greetings)


def get_custom_css():
    if not (css_id := int_or_none(request.args.get("css"))):
        return None
    return db.session.query(UserCSS).filter(UserCSS.id == css_id).first()


def parse_css_variable(css):
    CSS_VARIABLES_TEMPLATE = """:root {
      /*--<var>: <value>*/
      --modal: %(modal)s;
      --noroleusers: %(noroleusers)s;
      --main: %(main)s;
      --placeholder: %(placeholder)s;
      --sidebardivider: %(sidebardivider)s;
      --leftsidebar: %(leftsidebar)s;
      --rightsidebar: %(rightsidebar)s;
      --header: %(header)s;
      --chatmessage: %(chatmessage)s;
      --discrim: %(discrim)s;
      --chatbox: %(chatbox)s;
    }"""
    if not css:
        return None
    else:
        variables = css.css_variables
        if variables:
            variables = json.loads(variables)
            return CSS_VARIABLES_TEMPLATE % variables
    return None


def parse_url_domain(url):
    parsed = urlparse(url)
    return parsed.netloc if parsed.netloc != "" else url


def is_peak(guild_id):
    usrs = get_online_embed_user_keys(guild_id)
    return (
        len(usrs["AuthenticatedUsers"]) + len(usrs["UnauthenticatedUsers"])
    ) > 10


@embed.route("/<int:guild_id>")
def guild_embed(guild_id):
    if not (guild := bot_http_client.get_guild(guild_id)):
        log.warning("could not get guild '%s' from redis", guild_id)
        abort(404)

    try:
        db_guild = (
            db.session.query(Guilds).filter(Guilds.guild_id == guild_id).first()
        )
    except sqlalchemy.exc.OperationalError:
        # we sometimes loose connection with the database and have to reconnect
        # This seems to be the first db query we hit when loading the embed
        # So retry once
        log.warning("Lost connection to db - attempting to reconnect")
        db.session.rollback()
        time.sleep(1)
        # sqlalchemy.exc.PendingRollbackError: Can't reconnect until invalid transaction is rolled back.
        # (Background on this error at: https://sqlalche.me/e/14/8s2b)
        db.session.begin()
        db_guild = (
            db.session.query(Guilds).filter(Guilds.guild_id == guild_id).first()
        )
        log.info("Reconnected to db")

    if not db_guild:
        log.warning("found guild '%s' in redis but not in db", guild_id)
        abort(404)

    guild_dict = {
        "id": guild["id"],
        "name": guild["name"],
        "unauth_users": db_guild.unauth_users,
        "icon": guild["icon"],
        "invite_link": db_guild.invite_link,
        "invite_domain": parse_url_domain(db_guild.invite_link),
        "post_timeout": db_guild.post_timeout,
    }

    customcss = get_custom_css()

    return render_template(
        "embed.html.j2",
        disabled=str(guild_id) in list_disabled_guilds(),
        login_greeting=get_logingreeting(),
        guild_id=guild_id,
        guild=guild_dict,
        generate_guild_icon=generate_guild_icon_url,
        unauth_enabled=guild_query_unauth_users_bool(guild_id),
        visitors_enabled=guild_accepts_visitors(guild_id),
        unauth_captcha_enabled=guild_unauthcaptcha_enabled(guild_id),
        client_id=config["client-id"],
        recaptcha_site_key=config["recaptcha-site-key"],
        css=customcss,
        cssvariables=parse_css_variable(customcss),
        same_target=request.args.get("sametarget", False) == "true",
        userscalable=request.args.get("userscalable", "True")
        .lower()
        .startswith("t"),
        fixed_sidenav=request.args.get("fixedsidenav", "False")
        .lower()
        .startswith("t"),
        is_peak=request.args.get("forcepeak", False) == "1"
        or is_peak(guild_id),
        enable_code_highlighting=config["enable-code-highlighting"],
        cdn_domain=config["cdn-domain"],
    )


@embed.route("/signin_complete")
def signin_complete():
    return render_template(
        "signin_complete.html.j2",
        session=(serializer.dumps(copy.deepcopy(dict(session)))),
    )


@embed.route("/login_discord")
def login_discord():
    return redirect(
        url_for(
            "user.login_authenticated",
            redirect=url_for(
                "embed.signin_complete", _external=True, _scheme="https"
            ),
        )
    )


@embed.route("/noscript")
def noscript():
    return render_template("noscript.html.j2")


@embed.route("/cookietest1")
def cookietest1():
    js = "window._3rd_party_test_step1_loaded();"
    response = make_response(
        js, 200, {"Content-Type": "application/javascript"}
    )

    if not config.get("disable-samesite-cookie-flag", False):
        response.set_cookie(
            "third_party_c_t", "works", max_age=30, samesite="None"
        )
    else:
        response.set_cookie("third_party_c_t", "works", max_age=30)

    return response


@embed.route("/cookietest2")
def cookietest2():
    if (
        "third_party_c_t" in request.cookies
        and request.cookies["third_party_c_t"] == "works"
    ):
        res = "true"
    else:
        res = "false"
    js = f"window._3rd_party_test_step2_loaded({res})"

    response = make_response(
        js, 200, {"Content-Type": "application/javascript"}
    )

    if not config.get("disable-samesite-cookie-flag", False):
        response.set_cookie("third_party_c_t", "", expires=0, samesite="None")
    else:
        response.set_cookie("third_party_c_t", "", expires=0)

    return response
