#!/usr/bin/env python3
"""
Generator pasangan kunci agen untuk AgentPay.

Penggunaan:
    python tools/keygen.py --agent-id alice

Keluaran:
    - Kunci privat (rahasiakan!)
    - Kunci publik (daftarkan ke server)
    - Contoh perintah curl untuk registrasi
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Agar impor app.crypto berfungsi saat skrip dijalankan dari folder tools/
_direktori_backend = Path(__file__).resolve().parents[1]
if str(_direktori_backend) not in sys.path:
    sys.path.insert(0, str(_direktori_backend))

from app.crypto import Ed25519Crypto  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Menghasilkan pasangan kunci Ed25519 untuk AgentPay")
    parser.add_argument("--agent-id", required=True, help="Identitas agen")
    parser.add_argument("--balance", type=float, default=100.0, help="Saldo awal")
    args = parser.parse_args()

    privat, publik = Ed25519Crypto.generate_keypair()

    print("=" * 60)
    print(f"AgentPay — pasangan kunci untuk agen: {args.agent_id}")
    print("=" * 60)
    print("\nKUNCI PRIVAT (rahasiakan, jangan dibagikan):")
    print(privat)
    print("\nKUNCI PUBLIK (daftarkan ke server):")
    print(publik)

    stempel = datetime.now(timezone.utc).isoformat()
    pesan = {
        "agent_id": args.agent_id,
        "initial_balance": args.balance,
        "public_key": publik,
        "timestamp": stempel,
    }
    tanda = Ed25519Crypto.sign_message(privat, pesan)
    permintaan_lengkap = {**pesan, "signature": tanda}

    print("\nContoh permintaan registrasi (curl):")
    print("\ncurl -X POST http://localhost:8000/api/v1/agents \\")
    print("  -H 'Content-Type: application/json' \\")
    print(f"  -d '{json.dumps(permintaan_lengkap)}'")
    print("\n" + "=" * 60)

    nama_berkas = f"{args.agent_id}_keypair.json"
    with open(nama_berkas, "w", encoding="utf-8") as berkas:
        json.dump(
            {
                "agent_id": args.agent_id,
                "private_key": privat,
                "public_key": publik,
            },
            berkas,
            indent=2,
        )

    print(f"\nKunci disimpan ke: {nama_berkas}")
    print("PENTING: jangan mengunggah kunci privat ke repositori git.")


if __name__ == "__main__":
    main()
