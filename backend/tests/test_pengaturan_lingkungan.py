"""Cabang helper Settings (produksi / pengujian)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings


def test_is_production_dan_testing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("TESTING", "false")
    get_settings.cache_clear()
    pengaturan = get_settings()
    assert pengaturan.is_production is True
    assert pengaturan.is_testing is False
    get_settings.cache_clear()

    monkeypatch.setenv("ENVIRONMENT", "test")
    get_settings.cache_clear()
    assert get_settings().is_testing is True
    get_settings.cache_clear()


def test_log_level_tidak_valid_gagal_validasi() -> None:
    with pytest.raises(ValidationError):
        Settings(LOG_LEVEL="BUKAN_LEVEL")


def test_lingkungan_dev_dianggap_development(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    get_settings.cache_clear()
    assert get_settings().is_development is True
    get_settings.cache_clear()


def test_ambil_url_database_async_saat_testing_dengan_test_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://u:p@localhost:5432/agentpay_test_only",
    )
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    pengaturan = get_settings()
    assert "agentpay_test_only" in pengaturan.ambil_url_database_async()
    get_settings.cache_clear()
