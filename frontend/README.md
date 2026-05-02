# AgentPay — Frontend Dashboard

Dashboard React (Vite) untuk visualisasi agen, saldo, dan alur pembayaran terhadap backend FastAPI AgentPay.

## Fitur

- Kartu agen dengan saldo live dan tombol segarkan
- Form pembuatan agen (Ed25519, tanda kanonik sesuai backend)
- Form pembayaran antar agen dengan validasi saldo
- Daftar transaksi + grafik volume per status (Recharts)
- Alur escrow: terima (penerima) → konfirmasi (pengirim) → selesai / batalkan
- Polling 2 detik (transaksi) dan 5 detik (saldo) saat tab aktif
- Semai demo otomatis: `alice`, `bob`, `charlie` + satu transaksi contoh (jika belum ada di `sessionStorage`)

## Prasyarat

- Node.js 18+
- Backend berjalan di `http://localhost:8000` (lihat folder `../backend`)

## Setup

```bash
cd frontend
npm install
npm run dev
```

Buka **http://localhost:3000** (port diatur di `vite.config.js`).

Proxy Vite meneruskan `/api` dan `/health` ke backend sehingga tidak perlu mengatur CORS untuk origin yang sama.

## Skrip

| Skrip          | Keterangan                |
| -------------- | ------------------------- |
| `npm run dev`  | Server pengembangan Vite  |
| `npm run build`| Build produksi            |
| `npm run preview` | Pratinjau build statis |
| `npm run lint` | ESLint                    |
| `npm run format` | Prettier (format tulis) |

## Variabel lingkungan

Salin `.env.example` ke `.env` jika perlu:

- `VITE_API_BASE_URL` — kosong untuk dev dengan proxy; isi URL absolut jika frontend di-host terpisah dari API.

## Stack

- React 18, Vite 6
- Tailwind CSS 3.4
- Zustand, Axios, date-fns
- Lucide React, Recharts, Headless UI
- @noble/ed25519 (penandatanganan permintaan di browser — **hanya untuk demo**)

## Reset demo tersimpan

Hapus kunci `agentpay_demo_kunci_v1` di **Application → Session Storage** (DevTools) lalu muat ulang agar semai demo dijalankan ulang.
