"""Added patreon table

Revision ID: 16b4fdbbe155
Revises: 7d6484faaccd
Create Date: 2017-11-21 03:16:42.629612

"""

# revision identifiers, used by Alembic.
revision = "16b4fdbbe155"
down_revision = "7d6484faaccd"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "patreon",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("total_synced", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("patreon")
    # ### end Alembic commands ###
