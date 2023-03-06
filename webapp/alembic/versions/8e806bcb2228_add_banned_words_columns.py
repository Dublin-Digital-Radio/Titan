"""Add banned words columns

Revision ID: 8e806bcb2228
Revises: 176d26252734
Create Date: 2018-07-08 23:26:18.412175

"""

# revision identifiers, used by Alembic.
revision = "8e806bcb2228"
down_revision = "176d26252734"
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "guilds",
        sa.Column(
            "banned_words", sa.Text(), server_default="[]", nullable=False
        ),
    )
    op.add_column(
        "guilds",
        sa.Column(
            "banned_words_enabled",
            sa.Boolean(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "guilds",
        sa.Column(
            "banned_words_global_included",
            sa.Boolean(),
            server_default="0",
            nullable=False,
        ),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("guilds", "banned_words_global_included")
    op.drop_column("guilds", "banned_words_enabled")
    op.drop_column("guilds", "banned_words")
    # ### end Alembic commands ###
