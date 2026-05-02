# Panduan deployment produksi — AgentPay

Dokumen ini melengkapi README dengan detail operasional untuk lingkungan produksi.

## Prasyarat

- Docker Engine 20.10+ dan Docker Compose V2.
- Server dengan minimal **4 GB RAM** dan **10 GB** ruang disk kosong (lebih besar untuk log dan backup).
- Nama domain dan sertifikat TLS (disarankan Let’s Encrypt atau sertifikat perusahaan).

## Persiapan lingkungan

1. Salin variabel lingkungan: `cp backend/.env.example backend/.env` lalu sesuaikan **jangan** commit `.env`.
2. Set `ENVIRONMENT=production`, `DEBUG=false`, `LOG_LEVEL=WARNING`.
3. Ganti `SECRET_KEY`, kredensial Postgres, dan `REDIS_URL` ke endpoint internal yang aman.
4. Pastikan `DATABASE_URL` memakai hostname layanan Compose (mis. `postgres`) atau hostname internal cluster, bukan `localhost` dari sudut pandang container.

## Keamanan

- Jangan menyimpan rahasia di image Docker; gunakan secrets Compose, Docker Swarm secrets, atau penyedia secrets cloud.
- Batasi `CORS_ORIGINS` ke origin frontend produksi saja.
- Aktifkan TLS di reverse proxy (Traefik, nginx, atau load balancer) di depan backend dan frontend statis.
- Tinjau header keamanan di `frontend/nginx.conf` dan sesuaikan **Content-Security-Policy** dengan aset pihak ketiga yang benar-benar dipakai.

## Migrasi basis data

- Di container backend, skrip `entrypoint.sh` menunggu Postgres, lalu menjalankan `alembic upgrade head` sebelum Uvicorn.
- Untuk deployment tanpa entrypoint tersebut, jalankan manual: `docker compose run --rm backend alembic upgrade head`.

## Deployment tanpa downtime (ringkas)

1. Bangun image versi baru dengan tag semver.
2. Jalankan migrasi pada basis data (kompatibel mundur jika perlu rollback).
3. Rolling update: naikkan replika baru, tunggu health (`GET /health`, `GET /health/deep`), lalu matikan replika lama.
4. Untuk stack tunggal di Compose: `docker compose pull && docker compose up -d --no-deps backend` setelah image tersedia.

## Rollback

1. Kembalikan image backend (dan frontend jika berubah) ke tag sebelumnya.
2. Jika migrasi basis data tidak kompatibel mundur, siapkan skrip downgrade Alembic atau restore dari backup.

## Pemantauan dan alert

- **Metrik**: `GET /metrics` (format Prometheus).
- **Kesehatan**: `GET /health` (ringkas), `GET /health/deep` (database, Redis, disk, memori).
- Agregasi log: set `LOGGING_CONF_PATH` ke `/app/docker/logging.conf` di image backend (salinan dari `backend/docker/logging.conf`, JSON ke stdout).
- Hubungkan ke Prometheus + Grafana, atau setara cloud.

## Backup

- Postgres: jadwalkan `pg_dump` harian ke penyimpanan terpisah; uji restore berkala.
- Volume Redis: sesuaikan kebutuhan persistensi (AOF sudah diaktifkan di `docker-compose` contoh).

## Referensi

- [Docker Compose specification](https://github.com/compose-spec/compose-spec/blob/master/spec.md)
- [FastAPI deployment](https://fastapi.tiangolo.com/deployment/)
