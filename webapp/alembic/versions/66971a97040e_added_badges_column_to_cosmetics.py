"""Added badges column to cosmetics

Revision ID: 66971a97040e
Revises: 16b4fdbbe155
Create Date: 2017-12-07 04:30:25.639794

"""

# revision identifiers, used by Alembic.
revision = "66971a97040e"
down_revision = "16b4fdbbe155"
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "cosmetics",
        sa.Column("badges", sa.String(length=255), server_default="[]", nullable=False),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("cosmetics", "badges")
    # ### end Alembic commands ###
