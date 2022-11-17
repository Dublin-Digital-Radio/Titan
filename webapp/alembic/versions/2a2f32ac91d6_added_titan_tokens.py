"""Added Titan Tokens

Revision ID: 2a2f32ac91d6
Revises: 6fe130518448
Create Date: 2017-08-13 22:44:15.996936

"""

# revision identifiers, used by Alembic.
revision = "2a2f32ac91d6"
down_revision = "6fe130518448"
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "titan_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("tokens", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "token_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("timestamp", sa.TIMESTAMP(), nullable=False),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("net_tokens", sa.Integer(), nullable=False),
        sa.Column("start_tokens", sa.Integer(), nullable=False),
        sa.Column("end_tokens", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.alter_column(
        "cosmetics",
        "css",
        existing_type=mysql.TINYINT(display_width=1),
        type_=sa.Boolean(),
        existing_nullable=False,
    )
    op.alter_column(
        "guild_members",
        "active",
        existing_type=mysql.TINYINT(display_width=1),
        type_=sa.Boolean(),
        existing_nullable=False,
        existing_server_default=sa.text("'1'"),
    )
    op.alter_column(
        "guild_members",
        "banned",
        existing_type=mysql.TINYINT(display_width=1),
        type_=sa.Boolean(),
        existing_nullable=False,
        existing_server_default=sa.text("'0'"),
    )
    op.alter_column(
        "guilds",
        "bracket_links",
        existing_type=mysql.TINYINT(display_width=1),
        type_=sa.Boolean(),
        existing_nullable=False,
        existing_server_default=sa.text("'1'"),
    )
    op.alter_column(
        "guilds",
        "channels",
        existing_type=mysql.LONGTEXT(collation="utf8mb4_unicode_ci"),
        type_=sa.Text().with_variant(sa.Text(length=4294967295), "mysql"),
        existing_nullable=False,
    )
    op.alter_column(
        "guilds",
        "chat_links",
        existing_type=mysql.TINYINT(display_width=1),
        type_=sa.Boolean(),
        existing_nullable=False,
        existing_server_default=sa.text("'1'"),
    )
    op.alter_column(
        "guilds",
        "emojis",
        existing_type=mysql.LONGTEXT(collation="utf8mb4_unicode_ci"),
        type_=sa.Text().with_variant(sa.Text(length=4294967295), "mysql"),
        existing_nullable=False,
    )
    op.alter_column(
        "guilds",
        "roles",
        existing_type=mysql.LONGTEXT(collation="utf8mb4_unicode_ci"),
        type_=sa.Text().with_variant(sa.Text(length=4294967295), "mysql"),
        existing_nullable=False,
    )
    op.alter_column(
        "guilds",
        "unauth_users",
        existing_type=mysql.TINYINT(display_width=1),
        type_=sa.Boolean(),
        existing_nullable=False,
        existing_server_default=sa.text("'1'"),
    )
    op.alter_column(
        "guilds",
        "visitor_view",
        existing_type=mysql.TINYINT(display_width=1),
        type_=sa.Boolean(),
        existing_nullable=False,
    )
    op.alter_column(
        "guilds",
        "webhooks",
        existing_type=mysql.LONGTEXT(collation="utf8mb4_unicode_ci"),
        type_=sa.Text().with_variant(sa.Text(length=4294967295), "mysql"),
        existing_nullable=False,
    )
    op.alter_column(
        "unauthenticated_users",
        "revoked",
        existing_type=mysql.TINYINT(display_width=1),
        type_=sa.Boolean(),
        existing_nullable=False,
        existing_server_default=sa.text("'0'"),
    )
    op.alter_column(
        "user_css",
        "css",
        existing_type=mysql.LONGTEXT(collation="utf8mb4_unicode_ci"),
        type_=sa.Text().with_variant(sa.Text(length=4294967295), "mysql"),
        existing_nullable=True,
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "user_css",
        "css",
        existing_type=sa.Text().with_variant(sa.Text(length=4294967295), "mysql"),
        type_=mysql.LONGTEXT(collation="utf8mb4_unicode_ci"),
        existing_nullable=True,
    )
    op.alter_column(
        "unauthenticated_users",
        "revoked",
        existing_type=sa.Boolean(),
        type_=mysql.TINYINT(display_width=1),
        existing_nullable=False,
        existing_server_default=sa.text("'0'"),
    )
    op.alter_column(
        "guilds",
        "webhooks",
        existing_type=sa.Text().with_variant(sa.Text(length=4294967295), "mysql"),
        type_=mysql.LONGTEXT(collation="utf8mb4_unicode_ci"),
        existing_nullable=False,
    )
    op.alter_column(
        "guilds",
        "visitor_view",
        existing_type=sa.Boolean(),
        type_=mysql.TINYINT(display_width=1),
        existing_nullable=False,
    )
    op.alter_column(
        "guilds",
        "unauth_users",
        existing_type=sa.Boolean(),
        type_=mysql.TINYINT(display_width=1),
        existing_nullable=False,
        existing_server_default=sa.text("'1'"),
    )
    op.alter_column(
        "guilds",
        "roles",
        existing_type=sa.Text().with_variant(sa.Text(length=4294967295), "mysql"),
        type_=mysql.LONGTEXT(collation="utf8mb4_unicode_ci"),
        existing_nullable=False,
    )
    op.alter_column(
        "guilds",
        "emojis",
        existing_type=sa.Text().with_variant(sa.Text(length=4294967295), "mysql"),
        type_=mysql.LONGTEXT(collation="utf8mb4_unicode_ci"),
        existing_nullable=False,
    )
    op.alter_column(
        "guilds",
        "chat_links",
        existing_type=sa.Boolean(),
        type_=mysql.TINYINT(display_width=1),
        existing_nullable=False,
        existing_server_default=sa.text("'1'"),
    )
    op.alter_column(
        "guilds",
        "channels",
        existing_typesa.Text().with_variant(sa.Text(length=4294967295), "mysql"),
        type_=mysql.LONGTEXT(collation="utf8mb4_unicode_ci"),
        existing_nullable=False,
    )
    op.alter_column(
        "guilds",
        "bracket_links",
        existing_type=sa.Boolean(),
        type_=mysql.TINYINT(display_width=1),
        existing_nullable=False,
        existing_server_default=sa.text("'1'"),
    )
    op.alter_column(
        "guild_members",
        "banned",
        existing_type=sa.Boolean(),
        type_=mysql.TINYINT(display_width=1),
        existing_nullable=False,
        existing_server_default=sa.text("'0'"),
    )
    op.alter_column(
        "guild_members",
        "active",
        existing_type=sa.Boolean(),
        type_=mysql.TINYINT(display_width=1),
        existing_nullable=False,
        existing_server_default=sa.text("'1'"),
    )
    op.alter_column(
        "cosmetics",
        "css",
        existing_type=sa.Boolean(),
        type_=mysql.TINYINT(display_width=1),
        existing_nullable=False,
    )
    op.drop_table("token_transactions")
    op.drop_table("titan_tokens")
    # ### end Alembic commands ###
