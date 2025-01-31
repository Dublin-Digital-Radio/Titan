import time
import datetime

from titanembeds.database import db


class DiscordBotsOrgTransactions(db.Model):
    __tablename__ = "discordbotsorg_transactions"
    id = db.Column(db.Integer, primary_key=True)  # Auto increment id
    user_id = db.Column(
        db.BigInteger, nullable=False
    )  # Discord user id of user
    # The timestamp of when the action took place
    timestamp = db.Column(db.TIMESTAMP, nullable=False)
    # Very short description of the action
    action = db.Column(db.String(255), nullable=False)
    # Discord user id of the referrer
    referrer = db.Column(db.BigInteger, nullable=True)

    def __init__(self, user_id, action, referrer=None):
        self.user_id = user_id
        self.action = action
        if referrer:
            self.referrer = referrer
        self.timestamp = datetime.datetime.fromtimestamp(time.time()).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
