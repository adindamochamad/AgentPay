#!/usr/bin/env bash
# Satu perintah untuk juri: membangun dan menaikkan stack AgentPay, lalu menampilkan URL.
set -euo pipefail

akar_proyek="$(cd "$(dirname "$0")" && pwd)"
cd "$akar_proyek"

if ! command -v docker >/dev/null 2>&1; then
  echo "Galat: Docker tidak terpasang atau tidak ada di PATH." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Galat: Docker Compose V2 diperlukan (perintah: docker compose)." >&2
  exit 1
fi

echo "==> Menghentikan kontainer lama (jika ada)..."
docker compose down --remove-orphans 2>/dev/null || true

echo "==> Membangun image dan menjalankan layanan..."
docker compose up --build -d --remove-orphans "$@"

echo "==> Menunggu backend sehat (maks ~120s)..."
batas_detik=120
mulai="$(date +%s)"
while true; do
  if curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    break
  fi
  sekarang="$(date +%s)"
  if (( sekarang - mulai > batas_detik )); then
    echo "Galat: backend tidak merespons /health dalam ${batas_detik}s." >&2
    docker compose ps
    docker compose logs --tail=80 backend || true
    exit 1
  fi
  sleep 2
done

echo "==> Menunggu frontend merespons (maks ~90s)..."
mulai_fe="$(date +%s)"
while true; do
  if curl -fsS "http://127.0.0.1:3000/" >/dev/null 2>&1; then
    break
  fi
  sekarang="$(date +%s)"
  if (( sekarang - mulai_fe > 90 )); then
    echo "Peringatan: frontend belum merespons; periksa log: docker compose logs frontend" >&2
    break
  fi
  sleep 2
done

echo ""
echo "AgentPay siap digunakan:"
echo "  - Frontend:  http://localhost:3000"
echo "  - API / docs: http://localhost:8000/docs"
echo "  - Health:     http://localhost:8000/health"
echo ""
echo "Log: docker compose logs -f"
echo "Hentikan: ./stop.sh"
