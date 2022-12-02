from titanembeds.database import db


class Administrators(db.Model):
    __tablename__ = "administrators"
    # Discord user id of user of an administrator
    user_id = db.Column(db.BigInteger, nullable=False, primary_key=True)


def get_administrators_list():
    q = db.session.query(Administrators).all()
    their_ids = []
    for admin in q:
        their_ids.append(str(admin.user_id))
    return their_ids
