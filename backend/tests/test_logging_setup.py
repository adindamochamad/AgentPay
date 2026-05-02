"""Uji pemuatan konfigurasi logging."""

from __future__ import annotations

import logging

import pytest

from app.config import Settings
from app.logging_setup import muat_konfigurasi_logging


def test_muat_tanpa_berkas_conf(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOGGING_CONF_PATH", raising=False)
    muat_konfigurasi_logging(Settings(LOG_LEVEL="INFO", TESTING=True))
    assert logging.getLogger("agentpay").level <= logging.INFO


def test_muat_path_tidak_ada(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("LOGGING_CONF_PATH", str(tmp_path / "tidak_ada.conf"))
    muat_konfigurasi_logging(Settings(LOG_LEVEL="INFO", TESTING=True))


def test_muat_dengan_conf_valid(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    # Salin minimal: gunakan berkas logging asli proyek jika ada di tree uji
    from pathlib import Path

    root_repo = Path(__file__).resolve().parents[2]
    sumber = root_repo / "docker" / "backend" / "logging.conf"
    if not sumber.is_file():
        pytest.skip("logging.conf tidak ditemukan di tree")
    monkeypatch.setenv("LOGGING_CONF_PATH", str(sumber))
    pengaturan_prod = Settings(
        ENVIRONMENT="production",
        LOG_LEVEL="INFO",
        TESTING=True,
    )
    muat_konfigurasi_logging(pengaturan_prod)
    logging.getLogger("agentpay").warning("smoke_logging_conf")
