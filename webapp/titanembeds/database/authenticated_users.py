from titanembeds.database import db


class AuthenticatedUsers(db.Model):
    __tablename__ = "authenticated_users"
    id = db.Column(db.Integer, primary_key=True)  # Auto increment id
    guild_id = db.Column(db.BigInteger, nullable=False)
    client_id = db.Column(
        db.BigInteger, nullable=False
    )  # Client ID of the authenticated user

    def __init__(self, guild_id, client_id):
        self.guild_id = guild_id
        self.client_id = client_id
