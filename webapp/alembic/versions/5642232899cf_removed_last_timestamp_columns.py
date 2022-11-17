"""Removed last timestamp columns

Revision ID: 5642232899cf
Revises: 0b7761d85555
Create Date: 2018-01-21 03:03:32.359959

"""

# revision identifiers, used by Alembic.
revision = "5642232899cf"
down_revision = "0b7761d85555"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("authenticated_users", "last_timestamp")
    op.drop_column("unauthenticated_users", "last_timestamp")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "unauthenticated_users",
        sa.Column(
            "last_timestamp",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.add_column(
        "authenticated_users",
        sa.Column(
            "last_timestamp",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
    )
    # ### end Alembic commands ###
