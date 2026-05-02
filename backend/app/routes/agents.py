import base64
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.signature_verification import dependensi_pembuatan_agen
from app.models import Agent
from app.schemas import AgentCreateSigned, AgentResponse, BalanceResponse
from app.utils.exceptions import AgentNotFoundException, DuplicateAgentException


router = APIRouter(prefix="/agents", tags=["agents"])
pola_agent_id = re.compile(r"^[A-Za-z0-9_]+$")


async def layanan_simpan_agent(sesi_database: AsyncSession, muatan: AgentCreateSigned) -> AgentResponse:
    """
    Menyimpan agen setelah data tervalidasi (dipanggil rute setelah verifikasi tanda,
    atau dipakai uji unit dengan objek muatan yang sudah diset manual).
    """
    if not pola_agent_id.match(muatan.agent_id):
        raise ValueError("agent_id hanya boleh alfanumerik dan underscore")

    try:
        byte_publik = base64.b64decode(muatan.public_key)
    except Exception as galat:
        raise ValueError("public_key bukan Base64 yang valid") from galat
    if len(byte_publik) != 32:
        raise ValueError("public_key Ed25519 harus 32 byte setelah decode Base64")

    async with sesi_database.begin():
        kueri_agent = select(Agent).where(Agent.agent_id == muatan.agent_id)
        hasil_agent = await sesi_database.execute(kueri_agent)
        agent_terdaftar = hasil_agent.scalar_one_or_none()
        if agent_terdaftar is not None:
            raise DuplicateAgentException(muatan.agent_id)

        agent_baru = Agent(
            agent_id=muatan.agent_id,
            balance=muatan.initial_balance,
            public_key=muatan.public_key,
        )
        sesi_database.add(agent_baru)

    return AgentResponse.model_validate(agent_baru)


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    muatan: AgentCreateSigned = Depends(dependensi_pembuatan_agen),
    sesi_database: AsyncSession = Depends(get_db),
) -> AgentResponse:
    return await layanan_simpan_agent(sesi_database, muatan)


@router.get("/{agent_id}/balance", response_model=BalanceResponse)
async def get_balance(agent_id: str, sesi_database: AsyncSession = Depends(get_db)) -> BalanceResponse:
    kueri_agent = select(Agent).where(Agent.agent_id == agent_id)
    hasil_agent = await sesi_database.execute(kueri_agent)
    agent_aktif = hasil_agent.scalar_one_or_none()
    if agent_aktif is None:
        raise AgentNotFoundException(agent_id)

    return BalanceResponse(
        agent_id=agent_aktif.agent_id,
        balance=agent_aktif.balance,
        as_of=datetime.now(timezone.utc),
    )
