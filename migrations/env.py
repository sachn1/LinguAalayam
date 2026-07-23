"""Alembic migration environment configuration."""

import os
from logging.config import fileConfig
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

from alembic import context
from linguaalayam.models.orm import Base

# Imported for its side effect of registering RequestLog on Base.metadata, so
# `alembic revision --autogenerate` sees it too. Unused directly in this module.
from linguaalayam.observability.models import RequestLog  # noqa: F401

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _db_url() -> str:
    """Construct the database URL from environment variables.

    Returns
    -------
    str
        The database URL.

    Raises
    ------
    RuntimeError
        If any required environment variables are missing.
    """
    required = {
        "DB_USER": os.getenv("DB_USER"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD"),
        "DB_HOST": os.getenv("DB_HOST"),
        "DB_PORT": os.getenv("DB_PORT"),
        "DB_NAME": os.getenv("DB_NAME"),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    sslmode = os.getenv("DB_SSLMODE", "")
    sslmode_param = f"?sslmode={sslmode}" if sslmode else ""
    return (
        f"postgresql+psycopg2://{required['DB_USER']}:{quote_plus(required['DB_PASSWORD'])}"
        f"@{required['DB_HOST']}:{required['DB_PORT']}"
        f"/{required['DB_NAME']}{sslmode_param}"
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=_db_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(_db_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
