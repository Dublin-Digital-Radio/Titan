import time
import datetime

from titanembeds.database import db


class TokenTransactions(db.Model):
    __tablename__ = "token_transactions"
    id = db.Column(db.Integer, primary_key=True)  # Auto increment id
    user_id = db.Column(
        db.BigInteger, nullable=False
    )  # Discord user id of user
    # The timestamp of when the action took place
    timestamp = db.Column(db.TIMESTAMP, nullable=False)
    # Very short description of the action
    action = db.Column(db.String(255), nullable=False)
    # Net change of the token amount
    net_tokens = db.Column(db.Integer, nullable=False)
    # Token amount before transaction
    start_tokens = db.Column(db.Integer, nullable=False)
    # Tokens after transaction
    end_tokens = db.Column(db.Integer, nullable=False)

    def __init__(self, user_id, action, net_tokens, start_tokens, end_tokens):
        self.user_id = user_id
        self.timestamp = datetime.datetime.fromtimestamp(time.time()).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        self.action = action
        self.net_tokens = net_tokens
        self.start_tokens = start_tokens
        self.end_tokens = end_tokens
