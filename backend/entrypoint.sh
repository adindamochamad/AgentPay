#!/bin/sh
# Menunggu Postgres siap, migrasi Alembic, seed opsional, lalu Uvicorn.
set -eu

host_pg="${POSTGRES_HOST:-postgres}"
user_pg="${POSTGRES_USER:-agentpay}"
db_pg="${POSTGRES_DB:-agentpay}"
batas_tunggu_detik="${POSTGRES_WAIT_TIMEOUT:-30}"

# Menunggu Postgres menerima koneksi (maksimal batas_tunggu_detik).
indeks_tunggu=0
while ! pg_isready -h "$host_pg" -p 5432 -U "$user_pg" -d "$db_pg" -q 2>/dev/null; do
  indeks_tunggu=$((indeks_tunggu + 1))
  if [ "$indeks_tunggu" -ge "$batas_tunggu_detik" ]; then
    echo "entrypoint: Postgres tidak siap setelah ${batas_tunggu_detik}s" >&2
    exit 1
  fi
  sleep 1
done

echo "entrypoint: menjalankan alembic upgrade head"
alembic upgrade head

# Seed demo: set SEED_DEMO=1 atau true (hanya lingkungan non-produksi).
nilai_seed="${SEED_DEMO:-}"
if [ "$nilai_seed" = "1" ] || [ "$nilai_seed" = "true" ]; then
  if [ "${ENVIRONMENT:-development}" = "production" ]; then
    echo "entrypoint: SEED_DEMO diabaikan di production" >&2
  else
    echo "entrypoint: menjalankan seed demo (opsional)"
    python -m scripts.seed_demo || echo "entrypoint: seed demo gagal (dilanjutkan)" >&2
  fi
fi

penangan_sinyal() {
  # Meneruskan TERM/INT ke proses anak jika ada (graceful shutdown uvicorn).
  if [ -n "${pid_uvicorn:-}" ]; then
    kill -TERM "$pid_uvicorn" 2>/dev/null || true
    wait "$pid_uvicorn" 2>/dev/null || true
  fi
  exit 0
}
trap penangan_sinyal TERM INT

echo "entrypoint: memulai uvicorn"
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
pid_uvicorn=$!
wait "$pid_uvicorn"
