import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError

from app.config import get_settings
from app.background_tasks import shutdown_background_tasks, start_background_tasks
from app.database import engine
from app.logging_konteks import id_permintaan_saat_ini
from app.logging_setup import muat_konfigurasi_logging
from app.routes.agents import router as agents_router
from app.routes.monitoring import router as monitoring_router
from app.routes.transactions import router as transactions_router
from app.schemas import HealthResponse
from app.utils.exceptions import (
    AgentNotFoundException,
    DuplicateAgentException,
    InsufficientBalanceException,
    InvalidAmountException,
    InvalidStateTransition,
    InvalidTransactionStateException,
    RateLimitExceededException,
    SelfPaymentNotAllowedException,
    TransactionExpiredException,
)

pengaturan = get_settings()
muat_konfigurasi_logging(pengaturan)
logger = logging.getLogger("agentpay")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Skema basis data dikelola lewat Alembic (lihat Dockerfile / README).
    start_background_tasks()
    try:
        yield
    finally:
        shutdown_background_tasks()
        await engine.dispose()


app = FastAPI(
    title="AgentPay Backend API",
    description=(
        "Production-grade payment infrastructure for autonomous AI agents. "
        "Enables trustless agent-to-agent transactions with Ed25519 cryptographic "
        "signatures and escrow-based settlement."
    ),
    version="1.0.0",
    contact={"name": "AgentPay Team", "email": "team@agentpay.local"},
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=pengaturan.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    id_permintaan = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = id_permintaan
    token_konteks = id_permintaan_saat_ini.set(id_permintaan)
    try:
        respons = await call_next(request)
        respons.headers["X-Request-ID"] = id_permintaan
        return respons
    finally:
        id_permintaan_saat_ini.reset(token_konteks)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    waktu_mulai = time.perf_counter()
    respons = await call_next(request)
    durasi_ms = (time.perf_counter() - waktu_mulai) * 1000
    logger.info(
        "%s %s -> %s (%.2f ms)",
        request.method,
        request.url.path,
        respons.status_code,
        durasi_ms,
    )
    return respons


@app.exception_handler(DuplicateAgentException)
async def duplicate_agent_handler(_request: Request, exc: DuplicateAgentException) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(AgentNotFoundException)
async def agent_not_found_handler(_request: Request, exc: AgentNotFoundException) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(InsufficientBalanceException)
async def insufficient_balance_handler(
    _request: Request, exc: InsufficientBalanceException
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(InvalidTransactionStateException)
async def invalid_transaction_state_handler(
    _request: Request, exc: InvalidTransactionStateException
) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(InvalidStateTransition)
async def invalid_state_transition_handler(
    _request: Request, exc: InvalidStateTransition
) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(TransactionExpiredException)
async def transaction_expired_handler(
    _request: Request, exc: TransactionExpiredException
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(RateLimitExceededException)
async def rate_limit_handler(_request: Request, exc: RateLimitExceededException) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": str(exc)})


@app.exception_handler(InvalidAmountException)
async def invalid_amount_handler(_request: Request, exc: InvalidAmountException) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(SelfPaymentNotAllowedException)
async def self_payment_handler(
    _request: Request, exc: SelfPaymentNotAllowedException
) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_request: Request, exc: IntegrityError) -> JSONResponse:
    logger.exception("IntegrityError: %s", exc)
    return JSONResponse(status_code=409, content={"detail": "Konflik data pada database"})


@app.exception_handler(DBAPIError)
async def dbapi_error_handler(_request: Request, exc: DBAPIError) -> JSONResponse:
    logger.exception("DBAPIError: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Kesalahan koneksi database"})


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("SQLAlchemyError: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Kesalahan umum database"})


@app.exception_handler(ValueError)
async def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(RequestValidationError)
async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(exc.errors())},
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


app.include_router(monitoring_router)
app.include_router(agents_router, prefix=pengaturan.API_V1_PREFIX)
app.include_router(transactions_router, prefix=pengaturan.API_V1_PREFIX)
