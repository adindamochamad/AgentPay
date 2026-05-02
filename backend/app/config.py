"""
Modul konfigurasi AgentPay.

Memuat pengaturan dari variabel lingkungan dengan validasi bertipe (Pydantic Settings).
"""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Pengaturan aplikasi dari environment / berkas .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Basis data
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://agentpay:agentpay_secret@localhost:5432/agentpay",
        description="URL async SQLAlchemy (postgresql+asyncpg://...)",
    )
    DATABASE_POOL_SIZE: int = Field(default=20, ge=1, le=100)
    DATABASE_MAX_OVERFLOW: int = Field(default=10, ge=0, le=50)
    DATABASE_ECHO: bool = Field(default=False)
    DATABASE_POOL_RECYCLE: int = Field(default=3600, ge=300, description="Detik sebelum koneksi pool didaur ulang")

    TEST_DATABASE_URL: Optional[str] = Field(
        default=None,
        description="URL basis data khusus pengujian (async). Jika kosong, uji memakai SQLite.",
    )

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_MAX_CONNECTIONS: int = Field(default=50, ge=1, le=200)

    # API
    API_V1_PREFIX: str = Field(default="/api/v1")
    PROJECT_NAME: str = Field(default="AgentPay")
    VERSION: str = Field(default="0.1.0")
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:5173",
        ]
    )

    # Keamanan
    SECRET_KEY: str = Field(default="dev-secret-change-in-production-use-openssl-rand-hex-32")
    SIGNATURE_MAX_AGE_SECONDS: int = Field(default=300, ge=60, le=3600)
    SIGNATURE_MAX_FUTURE_SKEW_SECONDS: int = Field(
        default=60,
        ge=0,
        le=600,
        description="Toleransi detik jika timestamp dianggap terlalu jauh ke masa depan",
    )

    # Lingkungan
    ENVIRONMENT: Literal["development", "staging", "production", "test", "dev"] = Field(
        default="development"
    )
    DEBUG: bool = Field(default=True)
    LOG_LEVEL: str = Field(default="INFO")
    TESTING: bool = Field(default=False, description="Mode pengujian (mis. lewati tugas latar belakang)")

    # Batas bisnis transaksi
    MAX_TRANSACTIONS_PER_HOUR: int = Field(default=100, ge=1)
    # Float: timeout sangat pendek memungkinkan pengujian e2e (nilai jam pecahan).
    TRANSACTION_TIMEOUT_HOURS: float = Field(default=1.0, ge=1e-9, le=168.0)
    MIN_TRANSACTION_AMOUNT: Decimal = Field(default=Decimal("0.00000001"))
    MAX_TRANSACTION_AMOUNT: Decimal = Field(default=Decimal("1000000"))

    # Fitur operasional (hari 1–3)
    ENABLE_BACKGROUND_TASKS: bool = Field(default=True)
    DISPUTE_LOG_PATH: str = Field(default="dispute_review.log")

    @field_validator("LOG_LEVEL")
    @classmethod
    def validasi_log_level(cls, nilai: str) -> str:
        diizinkan = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        atas = nilai.upper()
        if atas not in diizinkan:
            raise ValueError(f"LOG_LEVEL harus salah satu dari {sorted(diizinkan)}")
        return atas

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT in ("development", "dev")

    @property
    def is_testing(self) -> bool:
        return self.TESTING or self.ENVIRONMENT == "test"

    def ambil_url_database_async(self) -> str:
        """URL async untuk aplikasi (uji bisa memakai TEST_DATABASE_URL)."""
        if self.is_testing and self.TEST_DATABASE_URL:
            return str(self.TEST_DATABASE_URL)
        return str(self.DATABASE_URL)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
