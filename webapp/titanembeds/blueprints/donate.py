import patreon
import paypalrestsdk
from config import config
from quart import abort
from quart import current_app as app
from quart import redirect, render_template, request, session, url_for
from titanembeds.blueprints.user import user_bp
from titanembeds.database import (
    Cosmetics,
    add_badge,
    db,
    get_titan_token,
    set_titan_token,
)
from titanembeds.database.patreon import Patreon
from titanembeds.decorators import discord_users_only


@user_bp.route("/donate", methods=["GET"])
@discord_users_only()
async def donate_get():
    cosmetics = (
        db.session.query(Cosmetics)
        .filter(Cosmetics.user_id == session["user_id"])
        .first()
    )
    return await render_template("donate.html.j2", cosmetics=cosmetics)


def get_paypal_api():
    return paypalrestsdk.Api(
        {
            "mode": "sandbox" if app.config["DEBUG"] else "live",
            "client_id": config["paypal-client-id"],
            "client_secret": config["paypal-client-secret"],
        }
    )


@user_bp.route("/donate", methods=["POST"])
@discord_users_only()
async def donate_post():
    form = await request.form
    donation_amount = form.get("amount")
    if not donation_amount:
        abort(402)

    donation_amount = float(donation_amount)
    if donation_amount < 5 or donation_amount > 100:
        abort(412)

    donation_amount = "{0:.2f}".format(donation_amount)
    payer = {"payment_method": "paypal"}
    items = [
        {
            "name": "TitanEmbeds Donation",
            "price": donation_amount,
            "currency": "USD",
            "quantity": "1",
        }
    ]
    amount = {"total": donation_amount, "currency": "USD"}
    description = "Donate and support TitanEmbeds development."
    redirect_urls = {
        "return_url": url_for(
            "user.donate_confirm",
            success="true",
            _external=True,
            _scheme="https",
        ),
        "cancel_url": url_for("index", _external=True, _scheme="https"),
    }
    payment = paypalrestsdk.Payment(
        {
            "intent": "sale",
            "payer": payer,
            "redirect_urls": redirect_urls,
            "transactions": [
                {
                    "item_list": {"items": items},
                    "amount": amount,
                    "description": description,
                }
            ],
        },
        api=get_paypal_api(),
    )

    if payment.create():
        for link in payment.links:
            if link["method"] == "REDIRECT":
                return redirect(link["href"])

    return redirect(url_for("index"))


@user_bp.route("/donate/confirm")
@discord_users_only()
async def donate_confirm():
    if not request.args.get("success"):
        return redirect(url_for("index"))

    payment = paypalrestsdk.Payment.find(
        request.args.get("paymentId"), api=get_paypal_api()
    )
    if not payment.execute({"payer_id": request.args.get("PayerID")}):
        return redirect(url_for("index"))

    trans_id = str(
        payment.transactions[0]["related_resources"][0]["sale"]["id"]
    )
    amount = float(payment.transactions[0]["amount"]["total"])
    tokens = int(amount * 100)
    action = "PAYPAL {}".format(trans_id)
    set_titan_token(session["user_id"], tokens, action)
    session["tokens"] = get_titan_token(session["user_id"])
    add_badge(session["user_id"], "supporter")
    db.session.commit()
    return redirect(url_for("user.donate_thanks", transaction=trans_id))


@user_bp.route("/donate/thanks")
@discord_users_only()
async def donate_thanks():
    tokens = get_titan_token(session["user_id"])
    transaction = request.args.get("transaction")
    return await render_template(
        "donate_thanks.html.j2", tokens=tokens, transaction=transaction
    )


@user_bp.route("/donate", methods=["PATCH"])
@discord_users_only()
async def donate_patch():
    form = await request.form
    item = form.get("item")

    amount = int(form.get("amount"))
    if amount <= 0:
        abort(400)

    subtract_amt = 0
    entry = (
        db.session.query(Cosmetics)
        .filter(Cosmetics.user_id == session["user_id"])
        .first()
    )

    if item == "custom_css_slots":
        subtract_amt = 100
    if item == "guest_icon":
        subtract_amt = 300
        if entry is not None and entry.guest_icon:
            abort(400)
    if item == "send_rich_embed":
        subtract_amt = 300
        if entry is not None and entry.send_rich_embed:
            abort(400)

    amt_change = -1 * subtract_amt * amount
    subtract = set_titan_token(
        session["user_id"], amt_change, "BUY " + item + " x" + str(amount)
    )
    if not subtract:
        return "", 402

    session["tokens"] += amt_change
    if item == "custom_css_slots":
        if not entry:
            entry = Cosmetics(session["user_id"])
            entry.css_limit = 0
        entry.css = True
        entry.css_limit += amount
    if item == "guest_icon":
        if not entry:
            entry = Cosmetics(session["user_id"])
        entry.guest_icon = True
    if item == "send_rich_embed":
        if not entry:
            entry = Cosmetics(session["user_id"])
        entry.send_rich_embed = True
    db.session.add(entry)
    db.session.commit()
    return "", 204


@user_bp.route("/patreon")
@discord_users_only()
async def patreon_landing():
    return await render_template(
        "patreon.html.j2",
        pclient_id=config["patreon-client-id"],
        state="initial",
    )


@user_bp.route("/patreon/callback")
@discord_users_only()
async def patreon_callback():
    patreon_oauth_client = patreon.OAuth(
        config["patreon-client-id"], config["patreon-client-secret"]
    )

    tokens = patreon_oauth_client.get_tokens(
        request.args.get("code"),
        url_for("user.patreon_callback", _external=True, _scheme="https"),
    )
    if "error" in tokens:
        if "patreon" in session:
            del session["patreon"]
        return redirect(url_for("user.patreon_landing"))

    session["patreon"] = tokens

    return redirect(url_for("user.patreon_sync_get"))


def format_patreon_user(user):
    pledges = [
        {
            "id": p.id(),
            "attributes": p.attributes(),
        }
        for p in user.relationship("pledges")
    ]

    usrobj = {
        "id": user.id(),
        "attributes": user.attributes(),
        "pledges": pledges,
        "titan": {
            "eligible_tokens": 0,
            "total_cents_synced": 0,
            "total_cents_pledged": 0,
        },
    }

    if usrobj["pledges"]:
        usrobj["titan"]["total_cents_pledged"] = usrobj["pledges"][0][
            "attributes"
        ]["total_historical_amount_cents"]

    dbpatreon = (
        db.session.query(Patreon).filter(Patreon.user_id == user.id()).first()
    )
    if dbpatreon:
        usrobj["titan"]["total_cents_synced"] = dbpatreon.total_synced

    usrobj["titan"]["eligible_tokens"] = (
        usrobj["titan"]["total_cents_pledged"]
        - usrobj["titan"]["total_cents_synced"]
    )

    return usrobj


@user_bp.route("/patreon/sync", methods=["GET"])
@discord_users_only()
async def patreon_sync_get():
    if "patreon" not in session:
        return redirect(url_for("user.patreon_landing"))

    api_client = patreon.API(session["patreon"]["access_token"])

    user_response = api_client.fetch_user(
        None,
        {
            "pledge": [
                "amount_cents",
                "total_historical_amount_cents",
                "declined_since",
                "created_at",
                "pledge_cap_cents",
                "patron_pays_fees",
                "outstanding_payment_amount_cents",
            ]
        },
    )
    user = user_response.data()

    if not user:
        del session["patreon"]
        return redirect(url_for("user.patreon_landing"))

    return await render_template(
        "patreon.html.j2", state="prepare", user=format_patreon_user(user)
    )


@user_bp.route("/patreon/sync", methods=["POST"])
@discord_users_only()
async def patreon_sync_post():
    if "patreon" not in session:
        abort(401)

    api_client = patreon.API(session["patreon"]["access_token"])
    user_response = api_client.fetch_user(
        None,
        {
            "pledge": [
                "amount_cents",
                "total_historical_amount_cents",
                "declined_since",
                "created_at",
                "pledge_cap_cents",
                "patron_pays_fees",
                "outstanding_payment_amount_cents",
            ]
        },
    )

    user = user_response.data()
    if not (user):
        abort(403)

    usr = format_patreon_user(user)
    if usr["titan"]["eligible_tokens"] <= 0:
        return "", 402

    dbpatreon = (
        db.session.query(Patreon).filter(Patreon.user_id == usr["id"]).first()
    )
    if not dbpatreon:
        dbpatreon = Patreon(usr["id"])
    dbpatreon.total_synced = usr["titan"]["total_cents_pledged"]
    db.session.add(dbpatreon)

    set_titan_token(
        session["user_id"],
        usr["titan"]["eligible_tokens"],
        "PATREON {} [{}]".format(usr["attributes"]["full_name"], usr["id"]),
    )
    add_badge(session["user_id"], "supporter")
    session["tokens"] = get_titan_token(session["user_id"])
    db.session.commit()

    return "", 204


@user_bp.route("/patreon/thanks")
@discord_users_only()
async def patreon_thanks():
    return await render_template("patreon.html.j2", state="thanks")
