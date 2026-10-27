"""Alembic environment. Two ways in:

* the API calls `app.migrate.upgrade(connection)` at start-up (the connection is handed over in `config.attributes`);
* the CLI (`alembic upgrade head`, `alembic revision --autogenerate`) builds its own engine from ARIANE_DATABASE_URL
  or, failing that, from the application settings (no OpenBao lookup: give the full URL for a CLI run).
"""
from __future__ import annotations

import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app import models  # noqa: F401  (register tables)
from app.config import get_settings
from app.database import Base

config = context.config
target_metadata = Base.metadata


def run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async() -> None:
    engine = create_async_engine(config.get_main_option("sqlalchemy.url") or get_settings().database_url)
    async with engine.connect() as conn:
        await conn.run_sync(run)
    await engine.dispose()


if (connection := config.attributes.get("connection")) is not None:
    run(connection)
else:
    asyncio.run(run_async())
