<div align="center">

# AgentPay

**Payment infrastructure for the autonomous agent economy**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![Ed25519](https://img.shields.io/badge/Crypto-Ed25519-6B46C1?style=flat-square&logo=gnuprivacyguard&logoColor=white)](https://ed25519.cr.yp.to)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

<br/>

> *AI agents are becoming autonomous actors. When they trade services — who handles the money?*

AgentPay is a **production-grade REST API** that lets any AI agent send, receive, and settle payments — with **Ed25519 cryptographic proof** at every step and an **escrow-based state machine** that ensures neither side gets burned.

**One command. Four services. Zero trust required between agents.**

[Quick Start](#-quick-start) · [AI Agent Demo](#-live-ai-agent-demo) · [API Reference](#-api-reference) · [Architecture](#-architecture) · [Performance](#-performance)

</div>

---

## Why AgentPay?

| Problem | AgentPay's answer |
|---------|------------------|
| AI agents can't hold credit cards | Agent identity = Ed25519 keypair — no bank account needed |
| Manual payment flows don't scale | REST API any agent can call with plain HTTP + JSON |
| Either side can claim they never agreed | Every state change requires a **cryptographic signature** from the authorizing party |
| Money can get stuck mid-flight | Escrow-based flow: funds commit on initiation, release only on mutual confirmation |
| Centralized gateways = single point of failure | Self-hostable, no vendor lock-in, full audit trail in Postgres |

---

## Features

```
 ┌─────────────────────────────────────────────────────────────┐
 │                                                             │
 │   Ed25519 Signatures    Escrow State Machine    Anti-Replay │
 │   ──────────────────    ─────────────────────   ──────────  │
 │   Every sensitive        INITIATED → PENDING     Nonce +    │
 │   action cryptograph-    → CONFIRMED → SETTLED   timestamp  │
 │   ically signed by       with automatic          validation │
 │   the authorizing        rollback on timeout     per request│
 │   party                                                     │
 │                                                             │
 │   Two-Party Consent     Idempotency Keys         Dispute    │
 │   ─────────────────     ────────────────         ───────    │
 │   Receiver must sign     Safe retries without    Signed     │
 │   ACCEPT, sender must    double-charging via     justifi-   │
 │   sign CONFIRM — both    Idempotency-Key         cation +   │
 │   parties on the hook    HTTP header             auto-      │
 │                                                  rollback   │
 └─────────────────────────────────────────────────────────────┘
```

- **Production stack** — FastAPI async, PostgreSQL 16, Redis, Alembic migrations, Prometheus metrics
- **Row-level locking** — `SELECT FOR UPDATE` prevents double-spend under concurrent load
- **Structured JSON logging** + request-ID tracing on every HTTP request
- **84%+ test coverage** enforced — 20+ test files covering unit, integration, and E2E
- **One-command deploy** — `./start.sh` boots the full 4-service stack

---

## Transaction Flow

```
 Agent A (Buyer)                   AgentPay                   Agent B (Seller)
       │                               │                              │
       │── POST /transactions ────────>│  Status: INITIATED           │
       │   [signed by A's key]         │  A's balance: -$5 (escrowed) │
       │                               │                              │
       │                               │<─── POST /accept ────────────│
       │                               │     [signed by B's key]      │
       │                               │  Status: PENDING             │
       │                               │                              │
       │         [B delivers service]  │                              │
       │                               │                              │
       │── POST /confirm ─────────────>│  Status: SETTLED             │
       │   [signed by A's key]         │  B's balance: +$5            │
       │                               │                              │
```

> Funds are **committed** (not transferred) at INITIATED. Settlement only completes when **both parties** complete the cryptographic handshake. Either side can cancel before SETTLED — funds always return to sender.

---

## Quick Start

**Requirements:** Docker 20.10+, Docker Compose V2, free ports `3000 · 8000 · 5432 · 6379`

```bash
git clone https://github.com/adindamochamad/AgentPay.git
cd AgentPay
./start.sh
```

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:3000 |
| API + Swagger | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |
| Deep health (DB + Redis + disk) | http://localhost:8000/health/deep |
| Prometheus metrics | http://localhost:8000/metrics |

```bash
# Stop the stack
./stop.sh
```

> The backend auto-runs: `pg_isready` → `alembic upgrade head` → optional seed → Uvicorn

---

## Live AI Agent Demo

AgentPay ships with a **real two-agent demo** powered by the Anthropic API. Two Claude agents — a data buyer and a weather data provider — discover, negotiate, pay, and settle autonomously through the same API any other client would use.

```
[Agent A — Buyer]   "I need weather data for Jakarta. Budget: $10."
[Agent B — Seller]  "I provide Jakarta weather JSON for $5."
[Agent A]           → calls katalog_layanan_tersedia tool
[Agent A]           → calls pembayaran_buat tool → POST /transactions
[AgentPay]          Transaction abc-123 | Status: INITIATED | A balance: $5 escrowed
[Agent B]           → calls pantau_pembayaran_masuk → detects INITIATED tx
[Agent B]           → calls pembayaran_terima → POST /transactions/abc-123/accept
[AgentPay]          Status: PENDING
[Agent B]           → calls kirim_data_cuaca_jakarta → delivers payload
[Agent A]           → calls pembayaran_konfirmasi_penerimaan → POST /confirm
[AgentPay]          Status: SETTLED | A: $95 | B: $5
```

### Run it

```bash
# 1. Start the stack
./start.sh

# 2. Install demo dependencies
pip install anthropic requests cryptography

# 3. Run
export ANTHROPIC_API_KEY=sk-ant-...
python demo_ai_agents.py
```

**Optional env vars:**

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTPAY_HOST` | `http://127.0.0.1:8000` | Backend host |
| `ANTHROPIC_MODEL` | `claude-3-5-sonnet-20241022` | Claude model |
| `DEMO_BUYER_ID` | `buyer` | Buyer agent ID |
| `DEMO_SELLER_ID` | `seller` | Seller agent ID |

---

## Architecture

```
                       ┌──────────────────┐
                       │     Browser /    │
                       │   AI Agent SDK   │
                       └────────┬─────────┘
                                │ HTTP
                   ┌────────────▼─────────────┐
                   │    nginx (frontend)       │
                   │  React SPA · gzip · CSP  │
                   │  proxy /api /health /docs │
                   └────────────┬─────────────┘
                                │ agentpay_network
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
 ┌────────▼────────┐  ┌─────────▼────────┐  ┌────────▼────────┐
 │    backend      │  │   postgres 16    │  │     redis 7     │
 │  FastAPI :8000  │  │     :5432        │  │     :6379       │
 │  async · Ed25519│  │  SQLAlchemy ORM  │  │  health checks  │
 │  state machine  │  │  Alembic migrate │  │  rate limiting  │
 └─────────────────┘  └──────────────────┘  └─────────────────┘
```

### Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI (async), SQLAlchemy 2.x async, Alembic |
| Frontend | React 18, Vite, Tailwind CSS, Zustand, @noble/ed25519 |
| Database | PostgreSQL 16 with row-level locking (`SELECT FOR UPDATE`) |
| Cache / infra | Redis 7 (AOF persistence, memory limits) |
| Crypto | Ed25519 — same primitive as SSH keys and Git signatures |
| Observability | Prometheus metrics, structured JSON logs, X-Request-ID tracing |
| Packaging | Docker multi-stage builds, non-root user, Compose V2 |

---

## Security Model

Every state-changing API call requires a **valid Ed25519 signature** from the appropriate party:

| Action | Who must sign |
|--------|--------------|
| `POST /agents` | The agent itself (self-registration) |
| `POST /transactions` | The **sender** |
| `POST /transactions/{id}/accept` | The **receiver** only |
| `POST /transactions/{id}/confirm` | The **sender** only |
| `POST /transactions/{id}/cancel` | Either party |
| `POST /transactions/{id}/dispute` | Either party + signed justification |

**Anti-replay:** Every signed request includes a unique `nonce` (stored permanently) and a `timestamp` validated for freshness — replaying an intercepted request is impossible.

**Database constraints:** `balance >= 0`, `amount > 0`, and `from_agent ≠ to_agent` are enforced at the database level, not just in application code.

---

## API Reference

```
POST   /api/v1/agents                          Register a new agent (signed)
GET    /api/v1/agents/{agent_id}/balance       Get agent balance

POST   /api/v1/transactions                    Initiate payment (signed by sender)
GET    /api/v1/transactions                    List transactions (filter: agent_id, status)
GET    /api/v1/transactions/{id}               Get transaction detail
POST   /api/v1/transactions/{id}/accept        Accept escrow (signed by receiver)
POST   /api/v1/transactions/{id}/confirm       Confirm + settle (signed by sender)
POST   /api/v1/transactions/{id}/cancel        Cancel + refund (signed by either)
POST   /api/v1/transactions/{id}/dispute       Dispute with justification (signed)

GET    /health                                 Liveness probe
GET    /health/deep                            Readiness: DB + Redis + disk + memory
GET    /metrics                                Prometheus exposition format
GET    /docs                                   Interactive OpenAPI (Swagger UI)
```

Full interactive documentation at `/docs` on any running instance.

---

## Performance

Measured on Apple M1 Pro, Docker Desktop, `docker compose up --build -d`:

| Endpoint | Method | P50 | P95 | P99 | Throughput |
|----------|--------|-----|-----|-----|-----------|
| `/health` | GET | 6 ms | 8 ms | 11 ms | ~1537 req/s |
| `/api/v1/agents/{id}/balance` | GET | 17 ms | 20 ms | 112 ms | ~526 req/s |
| `/api/v1/transactions` | POST | 14 ms | 26 ms | 38 ms | ~60 req/s* |

\* POST transactions require unique Ed25519 signatures per request — throughput scales with parallel signers.

**Memory footprint (idle after load):**

| Container | Usage / Limit |
|-----------|--------------|
| Backend | 118 MiB / 512 MiB |
| PostgreSQL | 81 MiB / 1 GiB |
| Redis | 20 MiB / 256 MiB |
| Frontend (nginx) | 9.8 MiB / 256 MiB |

**Startup:** ~20 s warm (cached images) · `./start.sh` → stack ready

---

## Testing

```bash
# Backend unit + integration (84% coverage minimum enforced)
cd backend && pytest tests/ -v

# E2E against live Docker stack
./tests/run_e2e_tests.sh

# Frontend lint
cd frontend && npm test
```

| Suite | Files | What it covers |
|-------|-------|---------------|
| Unit | 20+ files | Crypto, state machine, settlement, routes, models |
| Integration | API flows | Full request lifecycle with real DB (SQLite in CI) |
| E2E | 2 files | Live HTTP flows against Docker stack |
| Performance | 1 file | Latency + 100-concurrent load on balance endpoint |

---

## Local Development

**Hot-reload backend + DB/Redis in Docker:**
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

**Frontend dev server (proxies to backend):**
```bash
cd frontend && npm install && npm run dev
```

**Backend without Docker:**
```bash
cd backend
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Port `5432/8000/3000` in use | Edit `ports:` in `docker-compose.yml` or stop the conflicting service |
| `orphan containers` warning | `./start.sh` uses `--remove-orphans` automatically |
| Migration fails on startup | `docker compose logs backend` — ensure postgres is healthy first |
| Redis fails in `/health/deep` | Set `REDIS_URL=redis://redis:6379/0` (hostname `redis` inside Compose network) |
| Frontend blank / 502 | Wait for backend to be healthy before hitting the UI |

```bash
# Stream backend logs
docker compose logs -f backend
```

---

## Project Structure

```
AgentPay/
├── backend/
│   ├── app/
│   │   ├── routes/          # agents, transactions, monitoring
│   │   ├── services/        # SettlementService (escrow logic)
│   │   ├── middleware/      # Ed25519 signature verification
│   │   ├── state_machine.py # Transaction state transitions
│   │   ├── crypto.py        # Ed25519 sign / verify utilities
│   │   └── models.py        # SQLAlchemy ORM models
│   ├── tests/               # 20+ test files
│   └── alembic/             # Database migrations
├── frontend/
│   └── src/
│       ├── components/      # Dashboard, PaymentFlow, AgentCard …
│       ├── utils/crypto.js  # Ed25519 in-browser (@noble/ed25519)
│       └── store/           # Zustand state management
├── demo_ai_agents.py        # Two-Claude autonomous payment demo
├── docker-compose.yml
└── start.sh / stop.sh
```

---

## Deployment

See [`DEPLOYMENT.md`](./DEPLOYMENT.md) for production configuration. Key checklist:

- Set `SECRET_KEY` via `openssl rand -hex 32`
- Set `DATABASE_URL`, `REDIS_URL`, `CORS_ORIGINS` in your secrets manager
- Set `ENVIRONMENT=production`, `DEBUG=false`
- Use the template in [`.env.production`](./.env.production) — **never commit real secrets**

---

<div align="center">

**Built for NandaHack 2026** · MIT Media Lab + HCLTech

*AgentPay — because the agent economy needs payment rails, not payment promises.*

</div>
