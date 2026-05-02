import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import create_engine, pool

from alembic import context

# Pastikan root backend ada di sys.path saat Alembic dijalankan dari mana pun
_direktori_backend = Path(__file__).resolve().parents[1]
if str(_direktori_backend) not in sys.path:
    sys.path.insert(0, str(_direktori_backend))

from app.config import get_settings  # noqa: E402
from app.database import Base  # noqa: E402

# Registrasi model agar metadata terisi lengkap
import app.models  # noqa: E402, F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def ambil_url_database_singkron() -> str:
    """Alembic pakai engine sinkron; konversi dari URL async yang dipakai aplikasi."""
    url = os.environ.get("DATABASE_URL") or get_settings().DATABASE_URL
    if url.startswith("sqlite+aiosqlite"):
        return url.replace("sqlite+aiosqlite", "sqlite+pysqlite")
    if url.startswith("postgresql+asyncpg"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    if url.startswith("postgresql+psycopg2"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://")
    return url


def run_migrations_offline() -> None:
    url = ambil_url_database_singkron()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = ambil_url_database_singkron()
    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as koneksi:
        context.configure(connection=koneksi, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
