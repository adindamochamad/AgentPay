#!/usr/bin/env python3
"""Skrip cepat: memuat pengaturan dari environment (jalankan dari folder backend)."""

from app.config import get_settings

if __name__ == "__main__":
    pengaturan = get_settings()
    print("Konfigurasi AgentPay")
    print(f"  Lingkungan: {pengaturan.ENVIRONMENT}")
    print(f"  URL basis data (async): {pengaturan.ambil_url_database_async()}")
    print(f"  Debug: {pengaturan.DEBUG}")
    print(f"  Awalan API: {pengaturan.API_V1_PREFIX}")
    print("Pengaturan berhasil dimuat.")
