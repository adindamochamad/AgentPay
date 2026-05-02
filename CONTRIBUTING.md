# Berkontribusi ke AgentPay

Terima kasih telah berminat memperbaiki AgentPay. Panduan singkat ini membantu PR tetap konsisten dan mudah direview.

## Gaya kode

- **Backend**: Python 3.11+, ketik eksplisit di modul baru; jalankan `black`, `flake8`, dan `mypy` sebelum PR (lihat README).
- **Frontend**: ESLint + Prettier sesuai konfigurasi di `frontend/`.
- Nama variabel/komentar baru: ikuti konvensi repositori (Indonesia untuk penamaan baru di backend bila relevan dengan aturan proyek).

## Pengujian

- Unit & integrasi backend: `cd backend && pip install -r requirements-dev.txt && pytest`.
- Cakupan minimal proyek: **84%** (lihat `pyproject.toml`).
- E2E terhadap stack Docker: `./tests/run_e2e_tests.sh` (membutuhkan Docker bebas port default).
- Tambahkan tes untuk perbaikan bug dan fitur baru yang memengaruhi perilaku API.

## Proses PR

1. Fork / branch dari `main` (atau branch utama repositori).
2. Satu PR fokus pada satu perubahan logis; hindari refactor besar tanpa diskusi.
3. Isi deskripsi PR dengan: konteks, pendekatan, risiko, dan cara verifikasi manual (jika ada).
4. Pastikan CI hijau sebelum minta review.

## Issue

- Jelaskan langkah reproduksi, perilaku yang diharapkan vs aktual, dan versi Docker/OS jika relevan.
- Lampirkan potongan log (tanpa rahasia).

## Lisensi

Dengan mengirim kontribusi, Anda menyetujui lisensi yang sama dengan repositori (lihat README).
