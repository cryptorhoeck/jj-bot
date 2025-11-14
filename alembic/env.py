"""Alembic environment configuration for JJ-Bot"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import config for database path
try:
    import config
    db_path = config.DATABASE_PATH
except ImportError:
    db_path = "data/trades.db"

# This is the Alembic Config object
config_obj = context.config

# Interpret the config file for Python logging
if config_obj.config_file_name is not None:
    fileConfig(config_obj.config_file_name)

# Target metadata for autogenerate support
# For now we'll manage migrations manually since we're using raw SQLite
target_metadata = None

# Override database URL from config
config_obj.set_main_option('sqlalchemy.url', f'sqlite:///{db_path}')


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config_obj.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config_obj.get_section(config_obj.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
