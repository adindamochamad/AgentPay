import os
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# URL basis data uji: Postgres jika TEST_DATABASE_URL disetel, selain itu SQLite berkas lokal.
URL_UJI_POSTGRES = os.environ.get("TEST_DATABASE_URL") or os.environ.get("AGENTPAY_TEST_DATABASE_URL")
if URL_UJI_POSTGRES:
    os.environ["DATABASE_URL"] = URL_UJI_POSTGRES
    os.environ.setdefault("TESTING", "true")
else:
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_agentpay.db")

os.environ.setdefault("API_V1_PREFIX", "/api/v1")
os.environ.setdefault("ENABLE_BACKGROUND_TASKS", "false")

_direktori_backend = str(Path(__file__).resolve().parents[1])
if _direktori_backend not in sys.path:
    sys.path.insert(0, _direktori_backend)

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

URL_MESIN_UJI = URL_UJI_POSTGRES or os.environ["DATABASE_URL"]


@pytest_asyncio.fixture(scope="session")
async def engine_test():
    mesin_uji = create_async_engine(URL_MESIN_UJI, future=True)
    async with mesin_uji.begin() as koneksi_database:
        await koneksi_database.run_sync(Base.metadata.drop_all)
        await koneksi_database.run_sync(Base.metadata.create_all)
    yield mesin_uji
    await mesin_uji.dispose()


@pytest_asyncio.fixture
async def pabrik_sesi_uji(engine_test):
    return async_sessionmaker(
        bind=engine_test,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture(autouse=True)
async def reset_data(engine_test) -> AsyncGenerator[None, None]:
    async with engine_test.begin() as koneksi_database:
        await koneksi_database.run_sync(Base.metadata.drop_all)
        await koneksi_database.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def client_api(pabrik_sesi_uji) -> AsyncGenerator[AsyncClient, None]:
    async def _get_db_override() -> AsyncGenerator[AsyncSession, None]:
        async with pabrik_sesi_uji() as sesi_database:
            yield sesi_database

    app.dependency_overrides[get_db] = _get_db_override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as klien:
        yield klien
    app.dependency_overrides.clear()
