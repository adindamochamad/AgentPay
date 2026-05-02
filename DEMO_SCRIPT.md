# Demo Script - Day 1

1. Jalankan `docker compose up --build`
2. Buat 2 agen via `POST /agents`
3. Lakukan transfer valid via `POST /transactions`
4. Ambil saldo kedua agen via `GET /agents/{id_agen}/balance`
5. Tunjukkan cache hit pada saldo kedua dengan request berulang
6. Tunjukkan penolakan transaksi saat saldo tidak cukup
