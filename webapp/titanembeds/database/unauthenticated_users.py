import random
import string

from titanembeds.database import db


class UnauthenticatedUsers(db.Model):
    __tablename__ = "unauthenticated_users"
    # Auto increment id
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    # Guild pertaining to the unauthenticated user
    guild_id = db.Column(db.BigInteger, nullable=False)
    # The username of the user
    username = db.Column(db.String(255), nullable=False)
    # The discriminator to distinguish unauth users with each other
    discriminator = db.Column(db.Integer, nullable=False)
    # The secret key used to identify the user holder
    user_key = db.Column(db.Text(), nullable=False)
    # The IP Address of the user
    ip_address = db.Column(db.String(255), nullable=False)
    # If the user's key has been revoked and a new one is required to be generated
    revoked = db.Column(db.Boolean(), nullable=False)

    def __init__(self, guild_id, username, discriminator, ip_address):
        self.guild_id = guild_id
        self.username = username
        self.discriminator = discriminator
        self.user_key = "".join(random.choice(string.ascii_letters) for _ in range(0, 32))
        self.ip_address = ip_address
        self.revoked = False

    def __repr__(self):
        return "<UnauthenticatedUsers {0} {1} {2} {3} {4} {5} {6}>".format(
            self.id,
            self.guild_id,
            self.username,
            self.discriminator,
            self.user_key,
            self.ip_address,
            self.revoked,
        )

    def isRevoked(self):
        return self.revoked

    def changeUsername(self, username):
        self.username = username
        return self.username

    def revokeUser(self):
        self.revoked = True
        return self.revoked


def query_unauthenticated_users_like(username, guild_id, discriminator):
    query = (
        db.session.query(UnauthenticatedUsers)
        .filter(UnauthenticatedUsers.guild_id == str(guild_id))
        .filter(UnauthenticatedUsers.username.ilike(f"%{username}%"))
    )
    if discriminator:
        query = query.filter(UnauthenticatedUsers.discriminator == discriminator)
    dbuser = query.order_by(UnauthenticatedUsers.id.desc()).first()
    return dbuser
