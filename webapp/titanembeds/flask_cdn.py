# https://github.com/paylogic/flask-cdn

import os

from quart import current_app, request
from quart import url_for as flask_url_for


def endpoint_match(endpoint, endpoints):
    if endpoint in endpoints:
        return True

    for x in endpoints:
        if endpoint.endswith(".%s" % x):
            return True

    return False


def url_for(endpoint, **values):
    app = current_app

    if app.config["CDN_DEBUG"] or not endpoint_match(
        endpoint, app.config["CDN_ENDPOINTS"]
    ):
        return flask_url_for(endpoint, **values)

    try:
        scheme = values.pop("_scheme")
    except KeyError:
        scheme = "http"
        cdn_https = app.config["CDN_HTTPS"]
        if cdn_https is True or (cdn_https is None and request.is_secure):
            scheme = "https"

    static_folder = app.static_folder
    if (
        request.blueprint is not None
        and request.blueprint in app.blueprints
        and app.blueprints[request.blueprint].has_static_folder
    ):
        static_folder = app.blueprints[request.blueprint].static_folder

    urls = app.url_map.bind(app.config["CDN_DOMAIN"], url_scheme=scheme)

    if app.config["CDN_TIMESTAMP"]:
        path = os.path.join(static_folder, values["filename"])
        values["t"] = int(os.path.getmtime(path))

    values["v"] = app.config["CDN_VERSION"]

    return urls.build(endpoint, values=values, force_external=True)


class CDN(object):
    """
    The CDN object allows your application to use Flask-CDN.

    When initialising a CDN object you may optionally provide your
    :class:`flask.Flask` application object if it is ready. Otherwise,
    you may provide it later by using the :meth:`init_app` method.

    :param app: optional :class:`flask.Flask` application object
    :type app: :class:`flask.Flask` or None
    """

    def __init__(self, app=None):
        """
        An alternative way to pass your :class:`flask.Flask` application
        object to Flask-CDN. :meth:`init_app` also takes care of some
        default `settings`_.

        :param app: the :class:`flask.Flask` application object.
        """
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        defaults = [
            ("CDN_DEBUG", app.debug),
            ("CDN_DOMAIN", None),
            ("CDN_HTTPS", None),
            ("CDN_TIMESTAMP", True),
            ("CDN_VERSION", None),
            ("CDN_ENDPOINTS", ["static"]),
        ]

        for k, v in defaults:
            app.config.setdefault(k, v)

        if app.config["CDN_DOMAIN"]:
            app.jinja_env.globals["url_for"] = url_for
