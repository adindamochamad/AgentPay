"""
Memuat konfigurasi logging dari berkas (produksi: JSON ke stdout).
"""

from __future__ import annotations

import logging
import logging.config
import os
from pathlib import Path

from app.config import Settings
from app.logging_konteks import id_permintaan_saat_ini


class SaringanRequestId(logging.Filter):
    """Menyisipkan waktu ISO dan id permintaan ke setiap rekaman log (field untuk JsonFormatter)."""

    def filter(self, record: logging.LogRecord) -> bool:
        from datetime import datetime, timezone

        # Nama field menghindari bentrok dengan atribut bawaan LogRecord.
        setattr(record, "waktu_iso", datetime.now(timezone.utc).isoformat())
        nilai_id = id_permintaan_saat_ini.get()
        setattr(record, "id_permintaan", nilai_id if nilai_id is not None else "-")
        return True


def muat_konfigurasi_logging(pengaturan: Settings) -> None:
    """
    Mengaktifkan logging.conf jika tersedia (Docker / produksi).
    Fallback: basicConfig sesuai LOG_LEVEL.
    """
    path_str = os.environ.get("LOGGING_CONF_PATH", "").strip()
    if not path_str:
        logging.basicConfig(level=getattr(logging, pengaturan.LOG_LEVEL, logging.INFO))
        return

    path_conf = Path(path_str)
    if not path_conf.is_file():
        logging.basicConfig(level=getattr(logging, pengaturan.LOG_LEVEL, logging.INFO))
        return

    level_root = "WARNING" if pengaturan.is_production else pengaturan.LOG_LEVEL
    level_uvicorn = "WARNING" if pengaturan.is_production else pengaturan.LOG_LEVEL

    logging.config.fileConfig(
        path_conf,
        defaults={
            "level_root": level_root,
            "level_uvicorn": level_uvicorn,
        },
        disable_existing_loggers=False,
    )
    # fileConfig format INI tidak memasang filters pada handler; tambahkan manual.
    saringan = SaringanRequestId()
    pengolah_sudah: set[int] = set()
    for pengelola in (
        logging.getLogger(),
        logging.getLogger("uvicorn"),
        logging.getLogger("uvicorn.access"),
        logging.getLogger("uvicorn.error"),
    ):
        for pengolah in pengelola.handlers:
            kunci = id(pengolah)
            if kunci in pengolah_sudah:
                continue
            pengolah.addFilter(saringan)
            pengolah_sudah.add(kunci)
