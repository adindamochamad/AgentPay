"""Memastikan lifespan FastAPI terpasang (scheduler latar belakang)."""

from starlette.testclient import TestClient

from app.main import app


def test_health_melalui_testclient_menjalankan_lifespan() -> None:
    with TestClient(app) as klien:
        respons = klien.get("/health")
    assert respons.status_code == 200
    assert respons.json()["status"] == "ok"
