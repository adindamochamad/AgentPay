"""Pengujian performa ringan terhadap API yang sedang berjalan."""

from __future__ import annotations

import concurrent.futures
import statistics
import time
from uuid import uuid4

from tanda_helper import badan_pembuatan_agen, pasangan_kunci_baru


def test_waktu_respons_saldo(klien_http, prefiks_api_v1: str) -> None:
    privat, publik = pasangan_kunci_baru()
    id_agen = f"e2e_perf_{uuid4().hex[:12]}"
    muatan = badan_pembuatan_agen(id_agen, "100.00", privat, publik)
    assert klien_http.post(f"{prefiks_api_v1}/agents", json=muatan, timeout=30).status_code == 201

    daftar_ms: list[float] = []
    for _ in range(15):
        t0 = time.perf_counter()
        r = klien_http.get(f"{prefiks_api_v1}/agents/{id_agen}/balance", timeout=10)
        daftar_ms.append((time.perf_counter() - t0) * 1000)
        assert r.status_code == 200

    median_ms = statistics.median(daftar_ms)
    # Target ideal <50ms; di CI/Docker sering lebih tinggi — gunakan batas realistis.
    assert median_ms < 500, f"median respons saldo {median_ms:.1f}ms terlalu lambat"


def test_muatan_bersamaan_get_saldo(klien_http, prefiks_api_v1: str) -> None:
    privat, publik = pasangan_kunci_baru()
    id_agen = f"e2e_ld_{uuid4().hex[:12]}"
    muatan = badan_pembuatan_agen(id_agen, "500.00", privat, publik)
    assert klien_http.post(f"{prefiks_api_v1}/agents", json=muatan, timeout=30).status_code == 201

    def satu_get(_: int) -> int:
        return klien_http.get(f"{prefiks_api_v1}/agents/{id_agen}/balance", timeout=30).status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as eksekutor:
        hasil = list(eksekutor.map(satu_get, range(100)))

    assert all(kode == 200 for kode in hasil)
