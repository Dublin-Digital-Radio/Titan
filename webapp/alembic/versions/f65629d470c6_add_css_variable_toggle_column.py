"""Add css variable toggle column

Revision ID: f65629d470c6
Revises: 058f970b85db
Create Date: 2017-09-07 23:08:34.344304

"""

# revision identifiers, used by Alembic.
revision = "f65629d470c6"
down_revision = "058f970b85db"
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "administrators",
        "id",
        existing_type=sa.BIGINT(),
        type_=sa.Integer(),
        autoincrement=True,
    )
    op.alter_column(
        "authenticated_users",
        "id",
        existing_type=sa.BIGINT(),
        type_=sa.Integer(),
        autoincrement=True,
    )
    op.alter_column(
        "authenticated_users",
        "last_timestamp",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.TIMESTAMP(),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "cosmetics",
        "id",
        existing_type=sa.BIGINT(),
        type_=sa.Integer(),
        autoincrement=True,
    )
    op.alter_column(
        "guild_members",
        "discriminator",
        existing_type=sa.BIGINT(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "guild_members",
        "id",
        existing_type=sa.BIGINT(),
        type_=sa.Integer(),
        autoincrement=True,
    )
    op.alter_column(
        "guilds",
        "id",
        existing_type=sa.BIGINT(),
        type_=sa.Integer(),
        autoincrement=True,
    )
    op.alter_column(
        "guilds",
        "mentions_limit",
        existing_type=sa.BIGINT(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "keyvalue_properties",
        "expiration",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.TIMESTAMP(),
        existing_nullable=True,
    )
    op.alter_column(
        "keyvalue_properties",
        "id",
        existing_type=sa.BIGINT(),
        type_=sa.Integer(),
        autoincrement=True,
    )
    op.alter_column(
        "messages",
        "edited_timestamp",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.TIMESTAMP(),
        existing_nullable=True,
    )
    op.alter_column(
        "messages",
        "id",
        existing_type=sa.BIGINT(),
        type_=sa.Integer(),
        autoincrement=True,
    )
    op.alter_column(
        "messages",
        "timestamp",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.TIMESTAMP(),
        nullable=False,
    )
    op.alter_column(
        "titan_tokens",
        "id",
        existing_type=sa.BIGINT(),
        type_=sa.Integer(),
        autoincrement=True,
    )
    op.alter_column(
        "titan_tokens",
        "tokens",
        existing_type=sa.BIGINT(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "token_transactions",
        "end_tokens",
        existing_type=sa.BIGINT(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "token_transactions",
        "id",
        existing_type=sa.BIGINT(),
        type_=sa.Integer(),
        autoincrement=True,
    )
    op.alter_column(
        "token_transactions",
        "net_tokens",
        existing_type=sa.BIGINT(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "token_transactions",
        "start_tokens",
        existing_type=sa.BIGINT(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "token_transactions",
        "timestamp",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.TIMESTAMP(),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "unauthenticated_bans",
        "id",
        existing_type=sa.BIGINT(),
        type_=sa.Integer(),
        autoincrement=True,
    )
    op.alter_column(
        "unauthenticated_bans",
        "last_discriminator",
        existing_type=sa.BIGINT(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "unauthenticated_bans",
        "timestamp",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.TIMESTAMP(),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "unauthenticated_users",
        "discriminator",
        existing_type=sa.BIGINT(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "unauthenticated_users",
        "id",
        existing_type=sa.BIGINT(),
        type_=sa.Integer(),
        autoincrement=True,
    )
    op.alter_column(
        "unauthenticated_users",
        "last_timestamp",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.TIMESTAMP(),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.add_column(
        "user_css",
        sa.Column("css_var_bool", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.alter_column("user_css", "css_variables", existing_type=sa.TEXT())
    op.alter_column(
        "user_css",
        "id",
        existing_type=sa.BIGINT(),
        type_=sa.Integer(),
        autoincrement=True,
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "user_css",
        "id",
        existing_type=sa.Integer(),
        type_=sa.BIGINT(),
        autoincrement=True,
    )
    op.alter_column("user_css", "css_variables", existing_type=sa.TEXT(), nullable=True)
    op.drop_column("user_css", "css_var_bool")
    op.alter_column(
        "unauthenticated_users",
        "last_timestamp",
        existing_type=sa.TIMESTAMP(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "unauthenticated_users",
        "id",
        existing_type=sa.Integer(),
        type_=sa.BIGINT(),
        autoincrement=True,
    )
    op.alter_column(
        "unauthenticated_users",
        "discriminator",
        existing_type=sa.Integer(),
        type_=sa.BIGINT(),
        existing_nullable=False,
    )
    op.alter_column(
        "unauthenticated_bans",
        "timestamp",
        existing_type=sa.TIMESTAMP(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "unauthenticated_bans",
        "last_discriminator",
        existing_type=sa.Integer(),
        type_=sa.BIGINT(),
        existing_nullable=False,
    )
    op.alter_column(
        "unauthenticated_bans",
        "id",
        existing_type=sa.Integer(),
        type_=sa.BIGINT(),
        autoincrement=True,
    )
    op.alter_column(
        "token_transactions",
        "timestamp",
        existing_type=sa.TIMESTAMP(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "token_transactions",
        "start_tokens",
        existing_type=sa.Integer(),
        type_=sa.BIGINT(),
        existing_nullable=False,
    )
    op.alter_column(
        "token_transactions",
        "net_tokens",
        existing_type=sa.Integer(),
        type_=sa.BIGINT(),
        existing_nullable=False,
    )
    op.alter_column(
        "token_transactions",
        "id",
        existing_type=sa.Integer(),
        type_=sa.BIGINT(),
        autoincrement=True,
    )
    op.alter_column(
        "token_transactions",
        "end_tokens",
        existing_type=sa.Integer(),
        type_=sa.BIGINT(),
        existing_nullable=False,
    )
    op.alter_column(
        "titan_tokens",
        "tokens",
        existing_type=sa.Integer(),
        type_=sa.BIGINT(),
        existing_nullable=False,
    )
    op.alter_column(
        "titan_tokens",
        "id",
        existing_type=sa.Integer(),
        type_=sa.BIGINT(),
        autoincrement=True,
    )
    op.alter_column(
        "messages",
        "timestamp",
        existing_type=sa.TIMESTAMP(),
        type_=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
    )
    op.alter_column(
        "messages",
        "id",
        existing_type=sa.Integer(),
        type_=sa.BIGINT(),
        autoincrement=True,
    )
    op.alter_column(
        "messages",
        "edited_timestamp",
        existing_type=sa.TIMESTAMP(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "keyvalue_properties",
        "id",
        existing_type=sa.Integer(),
        type_=sa.BIGINT(),
        autoincrement=True,
    )
    op.alter_column(
        "keyvalue_properties",
        "expiration",
        existing_type=sa.TIMESTAMP(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "guilds",
        "mentions_limit",
        existing_type=sa.Integer(),
        type_=sa.BIGINT(),
        existing_nullable=False,
        existing_server_default=sa.text("(-1)::bigint"),
    )
    op.alter_column(
        "guilds",
        "id",
        existing_type=sa.Integer(),
        type_=sa.BIGINT(),
        autoincrement=True,
    )
    op.alter_column(
        "guild_members",
        "id",
        existing_type=sa.Integer(),
        type_=sa.BIGINT(),
        autoincrement=True,
    )
    op.alter_column(
        "guild_members",
        "discriminator",
        existing_type=sa.Integer(),
        type_=sa.BIGINT(),
        existing_nullable=False,
    )
    op.alter_column(
        "cosmetics",
        "id",
        existing_type=sa.Integer(),
        type_=sa.BIGINT(),
        autoincrement=True,
    )
    op.alter_column(
        "authenticated_users",
        "last_timestamp",
        existing_type=sa.TIMESTAMP(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "authenticated_users",
        "id",
        existing_type=sa.Integer(),
        type_=sa.BIGINT(),
        autoincrement=True,
    )
    op.alter_column(
        "administrators",
        "id",
        existing_type=sa.Integer(),
        type_=sa.BIGINT(),
        autoincrement=True,
    )
    # ### end Alembic commands ###
