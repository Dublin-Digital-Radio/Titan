from titanembeds.database import db


class UserCSS(db.Model):
    __tablename__ = "user_css"
    id = db.Column(db.Integer, primary_key=True)  # Auto increment id
    name = db.Column(db.String(255), nullable=False)  # CSS Name
    # Discord client ID of the owner of the css (can edit)
    user_id = db.Column(db.BigInteger, nullable=False)
    # If css variables should be taken into consideration
    css_var_bool = db.Column(db.Boolean(), nullable=False, server_default="0")
    css_variables = db.Column(db.Text())  # Customizeable CSS Variables
    # CSS contents
    css = db.Column(db.Text().with_variant(db.Text(4294967295), "mysql"))

    def __init__(
        self, name, user_id, css_var_bool=False, css_variables=None, css=None
    ):
        self.name = name
        self.user_id = user_id
        self.css_var_bool = css_var_bool
        self.css_variables = css_variables
        self.css = css
