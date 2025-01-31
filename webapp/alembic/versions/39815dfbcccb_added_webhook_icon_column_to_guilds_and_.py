"""Added webhook icon column to guilds and cosmetics

Revision ID: 39815dfbcccb
Revises: d1b89c41bf16
Create Date: 2017-09-13 04:31:35.532918

"""

# revision identifiers, used by Alembic.
revision = "39815dfbcccb"
down_revision = "d1b89c41bf16"
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "cosmetics",
        sa.Column(
            "webhook_icon",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "guilds",
        sa.Column("webhook_icon", sa.String(length=255), nullable=True),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("guilds", "webhook_icon")
    op.drop_column("cosmetics", "webhook_icon")
    # ### end Alembic commands ###
