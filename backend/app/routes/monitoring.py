"""
Endpoint pemantauan: metrik Prometheus dan pemeriksaan kesehatan mendalam.
"""

from __future__ import annotations

import logging
import resource
import shutil
import sys
from typing import Any

import redis.asyncio as redis_asinkron
from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest

from app.config import get_settings
from app.database import cek_kesehatan_koneksi_database

router = APIRouter(tags=["monitoring"])
logger = logging.getLogger("agentpay.monitoring")


def _ambil_penggunaan_memori_proses_bytes() -> int:
    """RSS proses saat ini (Linux: KB dari ru_maxrss; macOS: byte)."""
    penggunaan = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return int(penggunaan)
    return int(penggunaan) * 1024


@router.get("/metrics")
async def metrik_prometheus() -> Response:
    """Metrik Prometheus (format teks exposition)."""
    muatan = generate_latest(REGISTRY)
    return Response(content=muatan, media_type=CONTENT_TYPE_LATEST)


@router.get("/health/deep")
async def kesehatan_mendalam() -> dict[str, Any]:
    """
    Pemeriksaan kesehatan detail: database, Redis, ruang disk, memori proses.
    """
    pengaturan = get_settings()
    hasil_basis_data = await cek_kesehatan_koneksi_database()

    redis_sehat = False
    pesan_redis: str | None = None
    try:
        klien = redis_asinkron.from_url(  # type: ignore[no-untyped-call]
            pengaturan.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        try:
            pong = await klien.ping()
            redis_sehat = bool(pong)
        finally:
            await klien.aclose()
    except Exception as galat:  # noqa: BLE001 — ringkas untuk health endpoint
        pesan_redis = str(galat)
        logger.warning("Redis health gagal: %s", galat)

    cakram = shutil.disk_usage("/")
    batas_disk_kritis_byte = 100 * 1024 * 1024
    disk_sehat = cakram.free >= batas_disk_kritis_byte

    memori_byte = _ambil_penggunaan_memori_proses_bytes()
    # Asumsi: batas lunak 512MB RSS untuk sinyal degraded (bukan OOM absolut)
    batas_memori_byte = 512 * 1024 * 1024
    memori_sehat = memori_byte < batas_memori_byte

    status_keseluruhan = "healthy"
    if not hasil_basis_data or not redis_sehat:
        status_keseluruhan = "unhealthy"
    elif not disk_sehat or not memori_sehat:
        status_keseluruhan = "degraded"

    return {
        "status": status_keseluruhan,
        "checks": {
            "database": {"ok": hasil_basis_data},
            "redis": {"ok": redis_sehat, "error": pesan_redis},
            "disk": {
                "ok": disk_sehat,
                "free_bytes": cakram.free,
                "total_bytes": cakram.total,
                "used_bytes": cakram.used,
            },
            "memory": {
                "ok": memori_sehat,
                "rss_bytes": memori_byte,
            },
        },
    }
