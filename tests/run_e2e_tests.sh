#!/usr/bin/env bash
# Menaikkan stack (dengan override e2e), menjalankan pytest e2e, menghasilkan laporan HTML, lalu menghentikan stack.
set -euo pipefail

akar_proyek="$(cd "$(dirname "$0")/.." && pwd)"
cd "$akar_proyek"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker diperlukan." >&2
  exit 1
fi

echo "==> Compose up (dengan docker-compose.e2e.yml)..."
docker compose -f docker-compose.yml -f docker-compose.e2e.yml up --build -d

bersihkan() {
  echo "==> Compose down..."
  docker compose -f docker-compose.yml -f docker-compose.e2e.yml down --remove-orphans
}
trap bersihkan EXIT

echo "==> Menunggu /health..."
for i in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    break
  fi
  sleep 2
  if [ "$i" -eq 60 ]; then
    echo "Timeout menunggu backend." >&2
    docker compose -f docker-compose.yml -f docker-compose.e2e.yml logs --tail=100 backend || true
    exit 1
  fi
done

echo "==> Memasang dependensi e2e..."
python3 -m pip install -q -r tests/e2e/requirements.txt

mkdir -p tests/e2e/reports
export E2E_BASE_URL="${E2E_BASE_URL:-http://127.0.0.1:8000}"
export PYTHONPATH="${akar_proyek}/tests/e2e"

echo "==> pytest e2e..."
python3 -m pytest tests/e2e -v \
  --html="tests/e2e/reports/e2e_report.html" \
  --self-contained-html \
  --junitxml="tests/e2e/reports/e2e_junit.xml"

echo "Laporan HTML: tests/e2e/reports/e2e_report.html"
