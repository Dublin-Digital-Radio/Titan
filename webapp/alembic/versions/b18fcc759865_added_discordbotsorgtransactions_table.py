"""Added DiscordBotsOrgTransactions table

Revision ID: b18fcc759865
Revises: dffebf852b41
Create Date: 2018-02-27 06:14:12.133576

"""

# revision identifiers, used by Alembic.
revision = "b18fcc759865"
down_revision = "dffebf852b41"
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "discordbotsorg_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("timestamp", sa.TIMESTAMP(), nullable=False),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("referrer", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("discordbotsorg_transactions")
    # ### end Alembic commands ###
