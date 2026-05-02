"""
Variabel konteks untuk request_id agar konsisten di log JSON dan middleware.
"""

from __future__ import annotations

from contextvars import ContextVar

id_permintaan_saat_ini: ContextVar[str | None] = ContextVar("id_permintaan_saat_ini", default=None)
