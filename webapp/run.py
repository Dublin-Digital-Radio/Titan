import subprocess

from config import config
from titanembeds.app import app, socketio


def init_debug():
    import os

    from quart import jsonify, request

    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # Testing oauthlib

    app.jinja_env.auto_reload = True
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    # Session viewer https://gist.github.com/babldev/502364a3f7c9bafaa6db
    def decode_flask_cookie(secret_key, cookie_str):
        import hashlib

        from itsdangerous import URLSafeTimedSerializer
        from quart.sessions import TaggedJSONSerializer

        salt = "cookie-session"
        serializer = TaggedJSONSerializer()
        signer_kwargs = {
            "key_derivation": "hmac",
            "digest_method": hashlib.sha1,
        }
        s = URLSafeTimedSerializer(
            secret_key,
            salt=salt,
            serializer=serializer,
            signer_kwargs=signer_kwargs,
        )
        return s.loads(cookie_str)

    @app.route("/session")
    async def session():
        cookie = request.cookies.get("session")
        if cookie:
            decoded = decode_flask_cookie(
                app.secret_key, request.cookies.get("session")
            )
        else:
            decoded = None
        return jsonify(session_cookie=decoded)

    @app.route("/github-update", methods=["POST"])
    async def github_update():
        try:
            subprocess.Popen("git pull", shell=True).wait()
        except OSError:
            return "ERROR"

    @app.route("/error")
    async def make_error():
        _var = 1 / 0
        return "OK"


if __name__ == "__main__":
    if config["debug"]:
        init_debug()

    socketio.run(app, host="0.0.0.0", port=3000, debug=config["debug"])
