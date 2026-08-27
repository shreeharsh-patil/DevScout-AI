"""
Alembic environment configuration for DevScout AI.

Reads DATABASE_URL from the environment variable, matching the same
logic used by database.py so migrations always target the correct DB.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import models so Alembic can detect them for autogeneration.
from database import Base  # noqa: F401 – ensure models are loaded

# this is the Alembic Config object
config = context.config

# Override sqlalchemy.url with the DATABASE_URL environment variable
# so it always matches the live database.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./devscout.db")
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL and not an Engine,
    so no actual DB connection is needed.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an Engine from the URL in the config and connects
    to the actual database.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
