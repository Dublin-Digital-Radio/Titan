"""Updated Primary keys away from the auto increment and use bigints for ids

Revision ID: dffebf852b41
Revises: 5642232899cf
Create Date: 2018-01-23 19:32:40.846345

"""

# revision identifiers, used by Alembic.
revision = "dffebf852b41"
down_revision = "5642232899cf"
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "administrators",
        "user_id",
        existing_type=sa.String(255),
        type_=sa.BIGINT(),
        postgresql_using="user_id::bigint",
    )
    # op.execute("ALTER TABLE administrators ALTER COLUMN user_id TYPE BIGINT USING user_id::bigint")
    op.drop_column("administrators", "id")
    op.execute("ALTER TABLE administrators ADD PRIMARY KEY (user_id);")
    op.execute(
        "ALTER TABLE authenticated_users ALTER COLUMN client_id DROP DEFAULT"
    )
    op.alter_column(
        "authenticated_users",
        "client_id",
        existing_type=sa.String(255),
        type_=sa.BIGINT(),
        postgresql_using="client_id::bigint",
    )
    # op.execute("ALTER TABLE authenticated_users ALTER COLUMN client_id TYPE BIGINT USING client_id::bigint")
    op.execute(
        "ALTER TABLE authenticated_users ALTER COLUMN guild_id DROP DEFAULT"
    )
    op.alter_column(
        "authenticated_users",
        "guild_id",
        existing_type=sa.String(255),
        type_=sa.BIGINT(),
        postgresql_using="guild_id::bigint",
    )
    # op.execute("ALTER TABLE authenticated_users ALTER COLUMN guild_id TYPE BIGINT USING guild_id::bigint")
    op.execute("ALTER TABLE cosmetics ALTER COLUMN user_id DROP DEFAULT")
    op.alter_column(
        "cosmetics",
        "user_id",
        existing_type=sa.String(255),
        type_=sa.BIGINT(),
        postgresql_using="user_id::bigint",
    )
    # op.execute("ALTER TABLE cosmetics ALTER COLUMN user_id TYPE BIGINT USING user_id::bigint")
    op.drop_column("cosmetics", "id")
    op.execute("ALTER TABLE cosmetics ADD PRIMARY KEY (user_id);")
    op.execute("ALTER TABLE disabled_guilds ALTER COLUMN guild_id DROP DEFAULT")
    op.alter_column(
        "disabled_guilds",
        "guild_id",
        existing_type=sa.String(255),
        type_=sa.BIGINT(),
        postgresql_using="guild_id::bigint",
    )
    # op.execute("ALTER TABLE disabled_guilds ALTER COLUMN guild_id TYPE BIGINT USING guild_id::bigint")
    op.drop_column("disabled_guilds", "id")
    op.execute("ALTER TABLE disabled_guilds ADD PRIMARY KEY (guild_id);")
    op.execute("ALTER TABLE guild_members ALTER COLUMN guild_id DROP DEFAULT")
    op.alter_column(
        "guild_members",
        "guild_id",
        existing_type=sa.String(255),
        type_=sa.BIGINT(),
        postgresql_using="guild_id::bigint",
    )
    # op.execute("ALTER TABLE guild_members ALTER COLUMN guild_id TYPE BIGINT USING guild_id::bigint")
    op.execute("ALTER TABLE guild_members ALTER COLUMN user_id DROP DEFAULT")
    op.alter_column(
        "guild_members",
        "user_id",
        existing_type=sa.String(255),
        type_=sa.BIGINT(),
        postgresql_using="user_id::bigint",
    )
    # op.execute("ALTER TABLE guild_members ALTER COLUMN user_id TYPE BIGINT USING user_id::bigint")
    op.execute("ALTER TABLE guilds ALTER COLUMN guild_id DROP DEFAULT")
    op.alter_column(
        "guilds",
        "guild_id",
        existing_type=sa.String(255),
        type_=sa.BIGINT(),
        postgresql_using="guild_id::bigint",
    )
    # op.execute("ALTER TABLE guilds ALTER COLUMN guild_id TYPE BIGINT USING guild_id::bigint")
    op.execute("ALTER TABLE guilds ALTER COLUMN owner_id DROP DEFAULT")
    op.alter_column(
        "guilds",
        "owner_id",
        existing_type=sa.String(255),
        type_=sa.BIGINT(),
        postgresql_using="owner_id::bigint",
    )
    # op.execute("ALTER TABLE guilds ALTER COLUMN owner_id TYPE BIGINT USING owner_id::bigint")
    op.drop_column("guilds", "id")
    op.execute("ALTER TABLE guilds ADD PRIMARY KEY (guild_id);")
    op.execute("ALTER TABLE messages ALTER COLUMN channel_id DROP DEFAULT")
    op.alter_column(
        "messages",
        "channel_id",
        existing_type=sa.String(255),
        type_=sa.BIGINT(),
        postgresql_using="channel_id::bigint",
    )
    # op.execute("ALTER TABLE messages ALTER COLUMN channel_id TYPE BIGINT USING channel_id::bigint")
    op.execute("ALTER TABLE messages ALTER COLUMN guild_id DROP DEFAULT")
    op.alter_column(
        "messages",
        "guild_id",
        existing_type=sa.String(255),
        type_=sa.BIGINT(),
        postgresql_using="guild_id::bigint",
    )
    # op.execute("ALTER TABLE messages ALTER COLUMN guild_id TYPE BIGINT USING guild_id::bigint")
    op.execute("ALTER TABLE messages ALTER COLUMN message_id DROP DEFAULT")
    op.alter_column(
        "messages",
        "message_id",
        existing_type=sa.String(255),
        type_=sa.BIGINT(),
        postgresql_using="message_id::bigint",
    )
    # op.execute("ALTER TABLE messages ALTER COLUMN message_id TYPE BIGINT USING message_id::bigint")
    op.drop_column("messages", "id")
    op.execute("ALTER TABLE messages ADD PRIMARY KEY (message_id);")
    op.execute("ALTER TABLE patreon ALTER COLUMN user_id DROP DEFAULT")
    op.alter_column(
        "patreon",
        "user_id",
        existing_type=sa.String(255),
        type_=sa.BIGINT(),
        postgresql_using="user_id::bigint",
    )
    # op.execute("ALTER TABLE patreon ALTER COLUMN user_id TYPE BIGINT USING user_id::bigint")
    op.drop_column("patreon", "id")
    op.execute("ALTER TABLE patreon ADD PRIMARY KEY (user_id);")
    op.execute("ALTER TABLE titan_tokens ALTER COLUMN user_id DROP DEFAULT")
    op.alter_column(
        "titan_tokens",
        "user_id",
        existing_type=sa.String(255),
        type_=sa.BIGINT(),
        postgresql_using="user_id::bigint",
    )
    # op.execute("ALTER TABLE titan_tokens ALTER COLUMN user_id TYPE BIGINT USING user_id::bigint")
    op.drop_column("titan_tokens", "id")
    op.execute("ALTER TABLE titan_tokens ADD PRIMARY KEY (user_id);")
    op.execute(
        "ALTER TABLE token_transactions ALTER COLUMN user_id DROP DEFAULT"
    )
    op.alter_column(
        "token_transactions",
        "user_id",
        existing_type=sa.String(255),
        type_=sa.BIGINT(),
        postgresql_using="user_id::bigint",
    )
    # op.execute("ALTER TABLE token_transactions ALTER COLUMN user_id TYPE BIGINT USING user_id::bigint")
    op.execute(
        "ALTER TABLE unauthenticated_bans ALTER COLUMN guild_id DROP DEFAULT"
    )
    op.alter_column(
        "unauthenticated_bans",
        "guild_id",
        existing_type=sa.String(255),
        type_=sa.BIGINT(),
        postgresql_using="guild_id::bigint",
    )
    # op.execute("ALTER TABLE unauthenticated_bans ALTER COLUMN guild_id TYPE BIGINT USING guild_id::bigint")
    op.execute(
        "ALTER TABLE unauthenticated_bans ALTER COLUMN lifter_id DROP DEFAULT"
    )
    op.alter_column(
        "unauthenticated_bans",
        "lifter_id",
        existing_type=sa.String(255),
        type_=sa.BIGINT(),
        postgresql_using="lifter_id::bigint",
    )
    # op.execute("ALTER TABLE unauthenticated_bans ALTER COLUMN lifter_id TYPE BIGINT USING lifter_id::bigint")
    op.execute(
        "ALTER TABLE unauthenticated_bans ALTER COLUMN placer_id DROP DEFAULT"
    )
    op.alter_column(
        "unauthenticated_bans",
        "placer_id",
        existing_type=sa.String(255),
        type_=sa.BIGINT(),
        postgresql_using="placer_id::bigint",
    )
    # op.execute("ALTER TABLE unauthenticated_bans ALTER COLUMN placer_id TYPE BIGINT USING placer_id::bigint")
    op.execute(
        "ALTER TABLE unauthenticated_users ALTER COLUMN guild_id DROP DEFAULT"
    )
    op.alter_column(
        "unauthenticated_bans",
        "guild_id",
        existing_type=sa.String(255),
        type_=sa.BIGINT(),
        postgresql_using="guild_id::bigint",
    )
    # op.execute("ALTER TABLE unauthenticated_users ALTER COLUMN guild_id TYPE BIGINT USING guild_id::bigint")
    op.execute("ALTER TABLE user_css ALTER COLUMN user_id DROP DEFAULT")
    op.alter_column(
        "user_css",
        "user_id",
        existing_type=sa.String(255),
        type_=sa.BIGINT(),
        postgresql_using="user_id::bigint",
    )
    # op.execute("ALTER TABLE user_css ALTER COLUMN user_id TYPE BIGINT USING user_id::bigint")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "user_css",
        "user_id",
        existing_type=sa.BigInteger(),
        type_=sa.VARCHAR(length=255),
        existing_nullable=False,
    )
    op.alter_column(
        "unauthenticated_users",
        "guild_id",
        existing_type=sa.BigInteger(),
        type_=sa.VARCHAR(length=255),
        existing_nullable=False,
        existing_server_default=sa.text("''::character varying"),
    )
    op.alter_column(
        "unauthenticated_bans",
        "placer_id",
        existing_type=sa.BigInteger(),
        type_=sa.VARCHAR(length=255),
        existing_nullable=False,
        existing_server_default=sa.text("''::character varying"),
    )
    op.alter_column(
        "unauthenticated_bans",
        "lifter_id",
        existing_type=sa.BigInteger(),
        type_=sa.VARCHAR(length=255),
        existing_nullable=True,
    )
    op.alter_column(
        "unauthenticated_bans",
        "guild_id",
        existing_type=sa.BigInteger(),
        type_=sa.VARCHAR(length=255),
        existing_nullable=False,
        existing_server_default=sa.text("''::character varying"),
    )
    op.alter_column(
        "token_transactions",
        "user_id",
        existing_type=sa.BigInteger(),
        type_=sa.VARCHAR(length=255),
        existing_nullable=False,
    )
    op.add_column("titan_tokens", sa.Column("id", sa.INTEGER(), nullable=False))
    op.alter_column(
        "titan_tokens",
        "user_id",
        existing_type=sa.BigInteger(),
        type_=sa.VARCHAR(length=255),
        autoincrement=False,
    )
    op.add_column("patreon", sa.Column("id", sa.INTEGER(), nullable=False))
    op.alter_column(
        "patreon",
        "user_id",
        existing_type=sa.BigInteger(),
        type_=sa.VARCHAR(length=255),
        autoincrement=False,
    )
    op.add_column("messages", sa.Column("id", sa.INTEGER(), nullable=False))
    op.alter_column(
        "messages",
        "message_id",
        existing_type=sa.BigInteger(),
        type_=sa.VARCHAR(length=255),
        autoincrement=False,
        existing_server_default=sa.text("''::character varying"),
    )
    op.alter_column(
        "messages",
        "guild_id",
        existing_type=sa.BigInteger(),
        type_=sa.VARCHAR(length=255),
        existing_nullable=False,
        existing_server_default=sa.text("''::character varying"),
    )
    op.alter_column(
        "messages",
        "channel_id",
        existing_type=sa.BigInteger(),
        type_=sa.VARCHAR(length=255),
        existing_nullable=False,
        existing_server_default=sa.text("''::character varying"),
    )
    op.add_column("guilds", sa.Column("id", sa.INTEGER(), nullable=False))
    op.alter_column(
        "guilds",
        "owner_id",
        existing_type=sa.BigInteger(),
        type_=sa.VARCHAR(length=255),
        existing_nullable=False,
        existing_server_default=sa.text("''::character varying"),
    )
    op.alter_column(
        "guilds",
        "guild_id",
        existing_type=sa.BigInteger(),
        type_=sa.VARCHAR(length=255),
        autoincrement=False,
        existing_server_default=sa.text("''::character varying"),
    )
    op.alter_column(
        "guild_members",
        "user_id",
        existing_type=sa.BigInteger(),
        type_=sa.VARCHAR(length=255),
        existing_nullable=False,
        existing_server_default=sa.text("''::character varying"),
    )
    op.alter_column(
        "guild_members",
        "guild_id",
        existing_type=sa.BigInteger(),
        type_=sa.VARCHAR(length=255),
        existing_nullable=False,
        existing_server_default=sa.text("''::character varying"),
    )
    op.add_column(
        "disabled_guilds", sa.Column("id", sa.INTEGER(), nullable=False)
    )
    op.alter_column(
        "disabled_guilds",
        "guild_id",
        existing_type=sa.BigInteger(),
        type_=sa.VARCHAR(length=255),
        autoincrement=False,
    )
    op.add_column("cosmetics", sa.Column("id", sa.INTEGER(), nullable=False))
    op.alter_column(
        "cosmetics",
        "user_id",
        existing_type=sa.BigInteger(),
        type_=sa.VARCHAR(length=255),
        autoincrement=False,
    )
    op.alter_column(
        "authenticated_users",
        "guild_id",
        existing_type=sa.BigInteger(),
        type_=sa.VARCHAR(length=255),
        existing_nullable=False,
        existing_server_default=sa.text("''::character varying"),
    )
    op.alter_column(
        "authenticated_users",
        "client_id",
        existing_type=sa.BigInteger(),
        type_=sa.VARCHAR(length=255),
        existing_nullable=False,
        existing_server_default=sa.text("''::character varying"),
    )
    op.add_column(
        "administrators", sa.Column("id", sa.INTEGER(), nullable=False)
    )
    op.alter_column(
        "administrators",
        "user_id",
        existing_type=sa.BigInteger(),
        type_=sa.VARCHAR(length=255),
        autoincrement=False,
    )
    # ### end Alembic commands ###
