# Folder Docker — AgentPay

Berisi skrip dan konfigurasi yang dipakai container (init Postgres, logging legacy di root).

## Layanan Compose (ringkas)

| Layanan | Build / image | Port host (default) |
|---------|----------------|---------------------|
| `postgres` | `postgres:16-alpine` | 5432 |
| `redis` | `redis:7-alpine` | 6379 |
| `backend` | `./backend/Dockerfile` (context `./backend`) | 8000 |
| `frontend` | `./frontend/Dockerfile` (context `./frontend`) | 3000 → 80 |

Jaringan kustom: **`agentpay_network`**. Volume bernama: **`postgres_data`**, **`redis_data`**.

## Backend image

- **Context build**: `./backend` (bukan root repo) agar `.dockerignore` backend efektif.
- **Multi-stage**: tahap `builder` membuat wheel; tahap `runtime` memasang wheel, user non-root `agentpay` (UID 1000).
- **Entrypoint**: `backend/entrypoint.sh` — tunggu `pg_isready`, migrasi Alembic, seed opsional (`SEED_DEMO`), `uvicorn`.
- **Logging**: `LOGGING_CONF_PATH=/app/docker/logging.conf` (berkas disalin dari `backend/docker/logging.conf` saat build).
- **Kesehatan**: `HEALTHCHECK` di Dockerfile memanggil `GET /health`; Compose menambahkan probe serupa untuk orkestrasi.

## Frontend image

- Tahap **build**: `node:20-alpine`, `npm ci`, `npm run build` (`VITE_API_BASE_URL` kosong → klien memanggil path relatif `/api/v1`).
- Tahap **serve**: `nginx:alpine`, konfigurasi `frontend/nginx.conf` — SPA `try_files`, gzip, header keamanan, proxy ke `backend:8000`.

## Volume

- `postgres_data`: data Postgres persisten.
- `redis_data`: Redis AOF.

## Debug

```bash
docker compose ps
docker compose logs -f backend
docker compose exec backend sh -c 'pg_isready -h postgres -U agentpay'
docker compose exec postgres psql -U agentpay -d agentpay -c "SELECT 1"
```

## Dokumentasi resmi

- [PostgreSQL image](https://hub.docker.com/_/postgres)
- [Redis image](https://hub.docker.com/_/redis)
- [Docker Compose](https://docs.docker.com/compose/)
