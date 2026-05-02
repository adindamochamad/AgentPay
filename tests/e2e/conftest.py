"""
Fixture e2e: menunggu layanan siap dan menyediakan klien HTTP + pasangan agen uji.

Catatan: `pytest-docker` tersedia untuk eksperimen; skrip CI menaikkan stack lewat
`docker compose` lalu menjalankan pytest terhadap BASE_URL di host.
"""

from __future__ import annotations

import os
import time
from typing import Any, Generator

import pytest
import requests

from tanda_helper import badan_pembuatan_agen, pasangan_kunci_baru


@pytest.fixture(scope="session")
def url_dasar_api() -> str:
    return os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


@pytest.fixture(scope="session")
def awal_tunggu_layanan_siap(url_dasar_api: str) -> None:
    """Menunggu /health dari host hingga backend siap (stack Compose sudah jalan)."""
    batas = int(os.environ.get("E2E_WAIT_SECONDS", "120"))
    mulai = time.monotonic()
    galat_terakhir: str | None = None
    while time.monotonic() - mulai < batas:
        try:
            r = requests.get(f"{url_dasar_api}/health", timeout=3)
            if r.status_code == 200:
                return
        except requests.RequestException as exc:  # noqa: PERF203 — loop tunggu
            galat_terakhir = str(exc)
        time.sleep(1.5)
    pytest.fail(f"Layanan tidak siap setelah {batas}s: {galat_terakhir}")


@pytest.fixture
def klien_http(
    url_dasar_api: str,
    awal_tunggu_layanan_siap: None,
) -> requests.Session:
    sesi = requests.Session()
    sesi.headers.update({"Content-Type": "application/json"})
    return sesi


@pytest.fixture
def prefiks_api_v1(url_dasar_api: str) -> str:
    prefiks = os.environ.get("E2E_API_PREFIX", "/api/v1")
    return f"{url_dasar_api}{prefiks}"


@pytest.fixture
def sepasang_agen_siap(
    klien_http: requests.Session,
    prefiks_api_v1: str,
) -> Generator[dict[str, Any], None, None]:
    """
    Membuat dua agen dengan saldo awal melalui API (id unik per pengujian).
    """
    privat_a, publik_a = pasangan_kunci_baru()
    privat_b, publik_b = pasangan_kunci_baru()
    id_a = f"e2e_a_{os.urandom(4).hex()}"
    id_b = f"e2e_b_{os.urandom(4).hex()}"

    for id_agen, privat, publik, saldo in (
        (id_a, privat_a, publik_a, "10000.00"),
        (id_b, privat_b, publik_b, "10000.00"),
    ):
        muatan = badan_pembuatan_agen(id_agen, saldo, privat, publik)
        r = klien_http.post(f"{prefiks_api_v1}/agents", json=muatan, timeout=30)
        assert r.status_code == 201, r.text

    yield {
        "id_pengirim": id_a,
        "id_penerima": id_b,
        "privat_pengirim": privat_a,
        "publik_pengirim": publik_a,
        "privat_penerima": privat_b,
        "publik_penerima": publik_b,
    }