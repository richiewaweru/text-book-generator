from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


_TEST_DB_DIR = Path(tempfile.gettempdir()) / "textbook-agent-pytest"
_TEST_DB_DIR.mkdir(parents=True, exist_ok=True)
_TEST_DB_PATH = _TEST_DB_DIR / "app-runtime.db"

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB_PATH.as_posix()}"
os.environ.setdefault("RUN_MIGRATIONS_ON_STARTUP", "true")

from core.database.models import Base  # noqa: E402


@pytest.fixture
async def db_engine(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()
