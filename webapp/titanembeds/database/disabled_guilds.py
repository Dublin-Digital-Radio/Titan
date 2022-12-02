from titanembeds.database import db


class DisabledGuilds(db.Model):
    __tablename__ = "disabled_guilds"  # Auto increment id
    # Server id that is disabled
    guild_id = db.Column(db.BigInteger, nullable=False, primary_key=True)

    def __init__(self, guild_id):
        self.guild_id = guild_id


def list_disabled_guilds():
    q = db.session.query(DisabledGuilds).all()
    their_ids = []
    for guild in q:
        their_ids.append(str(guild.guild_id))
    return their_ids
