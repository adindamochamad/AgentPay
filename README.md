# AgentPay

AgentPay adalah infrastruktur pembayaran production-grade untuk ekonomi agen otonom: API bertanda Ed25519, saldo agen, dan alur transaksi dengan mesin status.

## 1. Ringkasan proyek

### Apa itu AgentPay

Platform **FastAPI** (backend) + **React / Vite** (frontend) untuk mengelola agen, saldo, dan transaksi antar agen dengan verifikasi kriptografis pada operasi sensitif.

### Fitur utama

- API versi `/api/v1` dengan dokumentasi OpenAPI (`/docs`).
- PostgreSQL, Redis, tugas latar belakang (kedaluwarsa transaksi).
- Endpoint `/health`, `/health/deep`, dan `/metrics` (Prometheus).
- Logging terstruktur JSON ke stdout.
- Orkestrasi Docker Compose: **satu perintah** menaikkan Postgres, Redis, backend, dan frontend (nginx + artefak statis).

## 2. Quick start (satu perintah untuk juri)

Dari root repositori:

```bash
./start.sh
```

Setara:

```bash
docker compose up --build -d --remove-orphans
```

Setelah sehat:

- **Frontend**: http://localhost:3000  
- **API & Swagger**: http://localhost:8000/docs  
- **Health**: http://localhost:8000/health dan http://localhost:8000/health/deep  
- **Metrik**: http://localhost:8000/metrics  

Backend menjalankan `pg_isready` → `alembic upgrade head` → seed demo (jika `SEED_DEMO=1` di Compose) → Uvicorn.

Menghentikan stack:

```bash
./stop.sh
```

## 3. Persyaratan sistem

- Docker 20.10+ dan Docker Compose V2 (`docker compose`)
- RAM bebas ±4 GB untuk build pertama; port host bebas: **3000**, **8000**, **5432**, **6379**
- Jika port **5432** bentrok dengan Postgres lokal, ubah pemetaan `ports:` pada layanan `postgres` di `docker-compose.yml`.

## 4. Arsitektur (ASCII)

```
                         +------------------+
                         |     Browser      |
                         +--------+---------+
                                  |
                    http://localhost:3000
                                  v
                       +-------------------+
                       |  nginx (frontend) |
                       |  SPA + gzip + CSP |
                       |  proxy /api,/health|
                       +---------+---------+
                                  |
                    +-------------+-------------+
                    |     agentpay_network      |
                    +-------------+-------------+
                                  |
          +-----------------------+-----------------------+
          |                       |                       |
          v                       v                       v
 +----------------+    +------------------+    +----------------+
 |    backend     |    |    postgres      |    |     redis      |
 | FastAPI :8000  |    |       :5432      |    |     :6379      |
 +--------+-------+    +------------------+    +----------------+
          |
   SQLAlchemy async + Alembic
```

## 5. Layanan Compose

| Layanan    | Peran |
|------------|--------|
| **postgres** | PostgreSQL 16; volume `postgres_data`; skrip init membuat DB `agentpay_test`. |
| **redis**    | Cache; volume `redis_data`, AOF, batas memori. |
| **backend**  | Image multi-stage dari `./backend`; user non-root; healthcheck `GET /health`. |
| **frontend** | Build Vite + nginx dari `./frontend`; mem-proxy `/api`, `/health`, `/metrics`, `/docs` ke backend. |

Jaringan: `agentpay_network` (bridge). Batas sumber daya: lihat blok `deploy.resources` di `docker-compose.yml`.

## 6. Pengembangan lokal

Stack produksi Compose (tanpa hot reload backend):

```bash
docker compose up --build
```

Hot reload backend + DB/Redis di Docker:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Frontend dev (terminal kedua, proxy ke API di host):

```bash
cd frontend && npm install && npm run dev
```

Backend tanpa Docker:

```bash
cd backend
pip install -r requirements-dev.txt
cp .env.example .env
# Sesuaikan DATABASE_URL ke localhost jika Postgres lokal
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Dependensi Python

- Produksi / image Docker: `backend/requirements.txt`
- Pengembangan & pytest: `backend/requirements-dev.txt` (`pip install -r requirements-dev.txt`)

## 7. Dokumentasi API

- Swagger: http://localhost:8000/docs  
- Penandatanganan Ed25519: `backend/README_SIGNATURES.md`, `backend/tools/keygen.py`

### Contoh alur: agen cuaca & pembayaran

```
[Agent A] I need weather data for Jakarta. Budget: $10
[Agent B] I provide weather data for $5
[Agent A] Creating payment: $5 to Agent B
[AgentPay] Transaction created: abc-123, Status: INITIATED
[Agent B] Payment detected, accepting...
[AgentPay] Status: PENDING
[Agent B] Delivering weather data: {"temp": "28°C", "humidity": "75%"}
[Agent A] Data received, confirming payment
[AgentPay] Status: SETTLED
[Result] Agent A: Balance 95 | Agent B: Balance 5
```

## 🤖 AI Agent Demo

AgentPay menyertakan skrip demo **dua agen Claude (Anthropic)** yang bertransaksi secara otonom lewat API yang sama dengan klien lain: pendaftaran agen bertanda, `POST /transactions`, `accept`, `confirm`, dan pencetakan saldo akhir.

### Running the AI Agent Demo

Pastikan stack AgentPay sudah jalan (mis. `./start.sh`), lalu dari root repositori:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
pip install anthropic requests cryptography
python demo_ai_agents.py
```

Secara default skrip menghubungi `http://127.0.0.1:8000/api/v1`. Variabel lingkungan opsional:

| Variabel | Keterangan |
|----------|------------|
| `AGENTPAY_HOST` | Host backend (default `http://127.0.0.1:8000`) |
| `AGENTPAY_API_PREFIX` | Prefiks API (default `/api/v1`) |
| `ANTHROPIC_MODEL` | Model Claude (default `claude-3-5-sonnet-20241022`) |
| `DEMO_BUYER_ID` / `DEMO_SELLER_ID` | ID agen demo (default `buyer` / `seller`; ubah jika ID bentrok dengan seed lokal) |

Jika agen `buyer` atau `seller` sudah terdaftar di basis data dengan kunci lain, registrasi akan gagal — gunakan ID unik atau basis data bersih.

## 8. Pengujian

| Jenis | Perintah |
|--------|----------|
| Unit / integrasi backend | `cd backend && pytest tests/ -v` |
| E2E (membutuhkan stack; disarankan override timeout pendek) | `./tests/run_e2e_tests.sh` |
| Frontend | `cd frontend && npm test` (saat ini menjalankan ESLint) |

E2E memakai `docker-compose.yml` + `docker-compose.e2e.yml` (timeout transaksi sangat pendek, tanpa seed). Laporan HTML: `tests/e2e/reports/e2e_report.html`.

## 9. Troubleshooting

| Gejala | Tindakan |
|--------|----------|
| Port 5432/8000/3000 sudah dipakai | Sesuaikan `ports:` di `docker-compose.yml` atau hentikan layanan yang bentrok. |
| `orphan containers` (mis. `agentpay_db`) | `./start.sh` memakai `--remove-orphans`; atau `docker compose down --remove-orphans`. |
| Migrasi gagal | `docker compose logs backend`; pastikan `postgres` sehat (`pg_isready`). |
| Redis gagal di `/health/deep` | Pastikan `REDIS_URL` memakai hostname `redis` dari dalam jaringan Compose. |
| Frontend kosong / 502 | `docker compose logs frontend`; pastikan backend sehat dulu. |

Log mengalir:

```bash
docker compose logs -f backend
```

## 10. Deployment produksi & lisensi

- Template variabel: [.env.production](./.env.production) (jangan commit rahasia).
- Panduan operasi: [DEPLOYMENT.md](./DEPLOYMENT.md).
- Detail Docker: [docker/README.md](./docker/README.md).
- Baseline performa & ukuran image: [PERFORMANCE.md](./PERFORMANCE.md).

**Lisensi & kredit:** NandaHack 2026; MIT Media Lab + HCLTech (sesuai ketentuan kompetisi).

---

## Endpoint API v1 (ringkas)

- `POST /api/v1/agents`
- `GET /api/v1/agents/{agent_id}/balance`
- `POST /api/v1/transactions`
- `POST /api/v1/transactions/{txn_id}/accept`
- `POST /api/v1/transactions/{txn_id}/confirm`
- `POST /api/v1/transactions/{txn_id}/cancel`
- `GET /api/v1/transactions/{txn_id}`
- `GET /api/v1/transactions` — paginasi `limit`, `offset`, filter `agent_id`, `status`
- `GET /health` — `GET /health/deep` — `GET /metrics`
