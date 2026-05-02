"""Uji endpoint pemantauan (/metrics, /health/deep)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_metrik_prometheus_berhasil() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as klien:
        jawaban = await klien.get("/metrics")
    assert jawaban.status_code == 200
    assert "text/plain" in jawaban.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_kesehatan_mendalam_struktur(client_api) -> None:
    jawaban = await client_api.get("/health/deep")
    assert jawaban.status_code == 200
    muatan = jawaban.json()
    assert muatan["status"] in ("healthy", "degraded", "unhealthy")
    assert "checks" in muatan
    assert "database" in muatan["checks"]
    assert "redis" in muatan["checks"]
    assert "disk" in muatan["checks"]
    assert "memory" in muatan["checks"]


@pytest.mark.asyncio
async def test_kesehatan_mendalam_dengan_redis_sehat(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.routes import monitoring as modul_monitoring

    klien_palsu = MagicMock()
    klien_palsu.ping = AsyncMock(return_value=True)
    klien_palsu.aclose = AsyncMock()

    def buat_klien_palsu(*_a: object, **_kw: object) -> MagicMock:
        return klien_palsu

    monkeypatch.setattr(modul_monitoring.redis_asinkron, "from_url", buat_klien_palsu)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as klien:
        jawaban = await klien.get("/health/deep")
    assert jawaban.status_code == 200
    assert jawaban.json()["checks"]["redis"]["ok"] is True
