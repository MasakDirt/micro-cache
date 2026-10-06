import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.app import create_app
from api.dependencies import get_session, get_transformer
from core.services.transformer import UpperCaseTransformer
from core.settings import Settings
from db.session import build_engine, build_session_factory

ALEMBIC_INI = Path(__file__).parents[2] / "alembic.ini"


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    if url := os.environ.get("TEST_DATABASE_URL"):
        yield url
        return

    os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer("postgres:17", driver="asyncpg") as container:
        yield container.get_connection_url()


@pytest.fixture(scope="session")
def migrated_db(postgres_url: str) -> str:
    config = Config(ALEMBIC_INI)
    config.set_main_option("sqlalchemy.url", postgres_url)
    command.upgrade(config, "head")
    return postgres_url


@pytest.fixture
def settings(migrated_db: str) -> Settings:
    return Settings(database_url=migrated_db, transformer_delay_seconds=0, _env_file=None)


@pytest.fixture
async def db_session(settings: Settings) -> AsyncIterator[AsyncSession]:
    engine = build_engine(settings)
    async with build_session_factory(engine)() as session:
        yield session
    async with engine.begin() as connection:
        await connection.execute(text("TRUNCATE transformed_strings, payloads"))
    await engine.dispose()


@pytest.fixture
def app(settings: Settings, db_session: AsyncSession, transformer: UpperCaseTransformer) -> FastAPI:
    application = create_app(settings)

    async def test_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    application.dependency_overrides[get_session] = test_session
    application.dependency_overrides[get_transformer] = lambda: transformer
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
