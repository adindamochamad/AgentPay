"""
Menyisipkan agen demo alice/bob jika belum ada (untuk SEED_DEMO di Docker).

Catatan: melewati API bertanda agar stack demo bisa naik tanpa klien eksternal.
"""

from __future__ import annotations

import asyncio
import logging
from decimal import Decimal

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Agent

logger = logging.getLogger("agentpay.seed_demo")

DATA_DEMO = (
    ("alice", "rtDJMThWIdLTKGyHJzBE+6imhcEmfa9+52Ry/hQXtW8=", Decimal("1000")),
    ("bob", "qgsf2fZL2ltloW+BCPtdnNozPAqwjRncYRyVwf6UiJo=", Decimal("500")),
)


async def jalankan_seed() -> None:
    async with SessionLocal() as sesi:
        async with sesi.begin():
            for id_agen, kunci_publik, saldo in DATA_DEMO:
                hasil = await sesi.execute(select(Agent).where(Agent.agent_id == id_agen))
                if hasil.scalar_one_or_none() is not None:
                    continue
                sesi.add(
                    Agent(
                        agent_id=id_agen,
                        public_key=kunci_publik,
                        balance=saldo,
                    )
                )
                logger.info("Seed: agen %s ditambahkan", id_agen)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(jalankan_seed())


if __name__ == "__main__":
    main()
