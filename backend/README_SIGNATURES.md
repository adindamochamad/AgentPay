# Autentikasi tanda Ed25519

## Ringkasan

Semua operasi AgentPay yang mengubah keadaan memerlukan tanda digital Ed25519 agar hanya pemegang kunci privat yang sah yang dapat bertindak atas nama agen.

## Menghasilkan kunci

Dari direktori `backend`:

```bash
python tools/keygen.py --agent-id alice --balance 100
```

Keluaran mencakup kunci privat (rahasiakan), kunci publik (didaftarkan ke server), contoh `curl`, dan berkas `alice_keypair.json`.

## Isi permintaan bertanda

Setiap permintaan bertanda memuat:

- `timestamp`: string ISO8601 dalam UTC; harus berada dalam jendela **5 menit** terakhir (server menolak timestamp terlalu lama atau terlalu jauh di masa depan).
- `signature`: tanda Base64 atas payload **tanpa** field `signature`, diserialkan JSON secara kanonik (kunci diurutkan, tanpa spasi tambahan).

Transaksi inisiasi juga membutuhkan:

- `nonce`: string unik; disimpan di basis data untuk mencegah replay permintaan yang sama.

Aksi pada transaksi (terima, konfirmasi, batal, sengketa) juga memakai `nonce` unik yang dicatat di tabel `jejak_nonce` setelah verifikasi berhasil.

## Menandatangani di Python

```python
from datetime import datetime, timezone
from uuid import uuid4

from app.crypto import Ed25519Crypto

privat = "…"  # Base64 kunci privat agen pengirim

stempel = datetime.now(timezone.utc).isoformat()
nonce_unik = str(uuid4())
pesan = {
    "from_agent": "alice",
    "to_agent": "bob",
    "amount": "10.00",
    "nonce": nonce_unik,
    "timestamp": stempel,
}
tanda = Ed25519Crypto.sign_message(privat, pesan)
permintaan = {**pesan, "signature": tanda}
```

Penting: nilai yang ditandatangani harus **sama persis** dengan yang dikirim sebagai JSON (tipe dan bentuk string angka mempengaruhi serialisasi kanonik).

## Aturan peran aksi

| Endpoint | Siapa yang menandatangani |
|----------|---------------------------|
| `POST .../accept` | Agen **penerima** (`to_agent`) |
| `POST .../confirm` | Agen **pengirim** (`from_agent`) |
| `POST .../cancel` | Pengirim **atau** penerima |
| `POST .../dispute` | Pengirim **atau** penerima |

Body aksi memuat `transaction_id` yang harus sama dengan UUID di path URL.

## Fitur keamanan

1. **Non-repudiation**: agen tidak dapat menyangkal transaksi yang ditandatangani dengan kunci privatnya.
2. **Anti-replay**: kombinasi timestamp, `nonce` transaksi, dan `jejak_nonce` untuk aksi.
3. **Anti-impersonation**: hanya pemegang kunci privat yang cocok dengan `public_key` terdaftar dapat membuat tanda sah.
4. **Tanpa rahasia bersama**: hanya kriptografi kunci publik.

## Pengujian

Contoh kunci uji ada di `tests/fixtures/alice_keypair.json` dan `tests/fixtures/bob_keypair.json`. Sebelum menguji API, jalankan `keygen` atau gunakan helper di `tests/bantuan_tanda.py`.

```bash
cd backend
pytest tests/test_crypto.py tests/test_agents.py tests/test_transactions.py -q
```
