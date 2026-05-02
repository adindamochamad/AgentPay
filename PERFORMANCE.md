# Baseline performa — AgentPay

Dokumen ini mencatat **pengukuran aktual** pada satu lingkungan referensi. Ulangi di hardware produksi Anda sebelum menetapkan SLA.

**Tanggal pengukuran:** 2026-05-02  
**Stack:** `docker compose up --build -d` (Postgres 16, Redis 7, backend FastAPI, frontend nginx)  
**Endpoint host:** `http://127.0.0.1:8000` (backend langsung; bukan proxy browser)

---

## System Specs

| Item | Nilai (lingkungan pengukuran) |
|------|--------------------------------|
| **CPU** | Apple M1 Pro |
| **RAM** | 16 GB |
| **OS** | macOS 26.4.1 (arm64) |
| **Docker** | Docker Desktop / engine Compose V2 |

---

## Results Summary

### API latency & throughput (ApacheBench)

Alat: `ab` (ApacheBench), kecuali dinyatakan lain. Untuk `GET /api/v1/agents/{id}/balance`, gunakan header `Accept: application/json` agar respons JSON konsisten (tanpa itu, beberapa klien dapat respons non-JSON).

| Endpoint | Metode | Permintaan | Konkurensi | P50 (ms) | P95 (ms) | P99 (ms) | Throughput (req/s) |
|----------|--------|------------|------------|----------|----------|----------|---------------------|
| `/health` | GET | 1000 | 10 | 6 | 8 | 11 | **~1537** |
| `/api/v1/agents/alice/balance` | GET | 1000 | 10 | 17 | 20 | 112 | **~526** |

*Catatan P99 saldo lebih tinggi sesekali (GC, I/O disk, penjadwal OS) — masih sub-ratusan ms pada pengukuran ini.*

### POST `/api/v1/transactions` (muatan bertanda unik)

`ab -p transaction.json` **tidak** cocok untuk beban berulang pada endpoint yang sama: setiap isi harus punya **nonce** dan tanda Ed25519 unik; mengirim ulang body yang sama memicu penolakan replay.

Pengukuran alternatif: **80 permintaan berurutan** dengan skrip Python (`tests/e2e/tanda_helper.py`) yang membuat badan baru per request.

| Metrik | Nilai (ms) |
|--------|------------|
| **P50** | 14.3 |
| **P95** | 26.0 |
| **P99** | 37.9 |
| **Min / Max** | 12.9 / 51.6 |
| **Mean** | 16.5 |
| **Setara throughput** (single-threaded client) | ~60 req/s |

Untuk beban tulis paralel nyata, gunakan banyak klien yang masing-masing menandatangani permintaan unik, atau orkestrasi uji (Locust/k6 dengan skrip).

### Perintah yang dipakai (reproduksi)

```bash
# Saldo agen (seed demo: alice) — wajib header Accept untuk respons JSON
ab -n 1000 -c 10 -H "Accept: application/json" \
  http://127.0.0.1:8000/api/v1/agents/alice/balance

# Health (probe ringan)
ab -n 1000 -c 10 http://127.0.0.1:8000/health
```

```bash
# POST transaksi: gunakan skrip tanda dinamis, bukan satu berkas statis
cd tests/e2e && E2E_BASE_URL=http://127.0.0.1:8000 pytest test_performance.py -v --tb=short
```

---

## Memory per service (Docker)

Perintah:

```bash
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"
```

**Snapshot pengukuran (idle ringan setelah beban):**

| Container | Mem usage / limit | Mem % |
|-----------|-------------------|-------|
| agentpay_frontend | 9.8 MiB / 256 MiB | ~3.9% |
| agentpay_backend | 118.6 MiB / 512 MiB | ~23% |
| agentpay_postgres | 81.6 MiB / 1 GiB | ~8% |
| agentpay_redis | 20.4 MiB / 256 MiB | ~8% |

Batas sumber daya di `docker-compose.yml` (`deploy.resources.limits`) tetap menjadi langkah pengaman untuk lingkungan demo.

---

## Ukuran image Docker

```bash
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep agentpay
```

**Contoh hasil (build lokal):**

| Image | Ukuran |
|-------|--------|
| `agentpay-backend:latest` | ~358 MB |
| `agentpay-frontend:latest` | ~92.6 MB |

Backend di atas target orientasi “&lt; 200 MB” di README — akibat runtime Python + dependensi; optimasi layer/wheel dapat mengecilkan lagi untuk rilis produksi.

---

## Startup performance

Perintah:

```bash
time ./start.sh
```

**Hasil (image sudah ter-cache, warm build):**

| Fase | Perkiraan |
|------|-----------|
| **Wall clock (`real`)** | **~20 s** (satu pengukuran pada mesin referensi) |
| **Isi skrip** | `docker compose down` → `up --build -d` → tunggu `/health` backend → tunggu `/` frontend |

Cold build pertama (unduh layer dasar, `npm ci`, wheel pip) bisa ** beberapa menit**; ukur ulang setelah cache Docker penuh untuk angka yang stabil.

---

## Load test results (pytest E2E)

```bash
cd tests/e2e
E2E_BASE_URL=http://127.0.0.1:8000 pytest test_performance.py -v --tb=short
```

| Tes | Yang diukur | Hasil pengukuran |
|-----|-------------|------------------|
| `test_waktu_respons_saldo` | 15× GET saldo agen baru; median &lt; 500 ms | **Lulus** |
| `test_muatan_bersamaan_get_saldo` | 100 GET paralel (20 worker) ke satu `agent_id` | **Lulus** (semua HTTP 200) |

Tes tidak mencetak histogram ke stdout; ambang **500 ms** median adalah guardrail CI, bukan laporan latensi detail.

---

## Database connection pool (konfigurasi)

Statistik pool runtime tidak diekspos lewat endpoint publik pada build ini. Nilai default dari `backend/app/config.py`:

| Parameter | Default | Keterangan |
|-----------|---------|------------|
| `DATABASE_POOL_SIZE` | 20 | Koneksi tetap di pool |
| `DATABASE_MAX_OVERFLOW` | 10 | Koneksi tambahan saat puncak |
| **Maks koneksi efektif** | **~30** | 20 + 10 overflow |
| `DATABASE_POOL_RECYCLE` | 3600 s | Daur ulang koneksi |

Sesuaikan via variabel lingkungan di deployment produksi (beban tinggi, banyak worker Uvicorn).

**Redis:** `REDIS_MAX_CONNECTIONS` default **50**. Endpoint saldo saat ini membaca saldo dari **PostgreSQL**; Redis dipakai antara lain untuk health `/health/deep` dan infrastruktur siap ekspansi (bukan cache saldo otomatis pada pengukuran ini).

---

## Concurrent request handling

- **GET `/health`:** ~1500+ req/s pada pengukuran `ab` (10 koneksi paralel, 1000 permintaan) — cocok untuk probe Kubernetes / load balancer.
- **GET saldo:** ~500+ req/s dengan pola yang sama; beban CPU/database naik dibanding `/health`.
- **POST transaksi:** throughput terbatas oleh verifikasi tanda Ed25519, validasi, dan transaksi DB per permintaan; gunakan nonce unik per call.

---

## Interpretation

1. **Latensi sub-100 ms** untuk operasi baca saldo dan **~15–25 ms** median untuk inisiasi transaksi bertanda pada laptop kelas dev memenuhi ekspektasi API sinkron untuk agen otonom.
2. **P99** pada `ab` dapat melonjak oleh kontensi port/host OS; di produksi, letakkan backend di belakang reverse proxy dengan keep-alive dan sesuaikan worker Uvicorn (`workers`, `uvicorn`) serta pool DB.
3. **Memori backend ~120 MiB** pada idle adalah baseline sehat untuk image Python; pantau RSS di bawah limit Compose (512 MiB).
4. **Startup ~20 s** dengan cache mengonfirmasi pengalaman “satu perintah” untuk juri; dokumentasikan cold build secara terpisah untuk ekspektasi realistis.
5. Ulangi semua angka pada **staging produksi** (CPU/RAM/jaringan berbeda); jangan jadikan tabel ini SLA hukum tanpa pengukuran ulang.

---

## Pembaruan baseline

Saat mengubah Dockerfile, dependensi utama, batas Compose, atau worker ASGI, jalankan ulang `ab`, `pytest tests/e2e/test_performance.py`, dan `docker stats`, lalu perbarui tabel di dokumen ini.
