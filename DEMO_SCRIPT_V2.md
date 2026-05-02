# AgentPay — Demo Video Script (V2)

**Target length:** ~5 minutes  
**Audience:** Judges, builders, technical + business  
**Format:** Screen recording + voiceover (or presenter to camera on intro/outro)

**How to use this doc**

- **Timecodes** = edit markers in your NLE (Premiere, DaVinci, Final Cut).
- **NARRATOR** = word-for-word voiceover (English; adjust for Bahasa if needed).
- **ON SCREEN** = what the viewer should see.
- **TERMINAL** = commands to type or paste.
- **API** = examples to flash on screen or show in Swagger (`/docs`).

**Video editor shorthand** (use as on-screen notes / timeline markers):

| Marker | Meaning |
|--------|---------|
| `[CUT TO: terminal]` | Hard cut from previous scene to full-screen terminal (or split: face + terminal). |
| `[CUT TO: browser]` | Cut to browser / Swagger UI. |
| `[CUT TO: title card]` | Cut to full-screen typography or logo sting. |
| `[ZOOM IN: …]` | Scale 100% → ~125–150% on region, 0.4–0.8s ease; hold 1–2s. |
| `[OVERLAY: "…"]` | Lower-third or centered text overlay; keep 1.5–3s unless VO is longer. |

---

## Pre-production checklist

| Item | Notes |
|------|--------|
| Clean Docker state | `docker compose down` then `./start.sh` for a fresh run |
| Browser | Single tab: dashboard `http://localhost:3000` |
| Terminal | Large font, dark theme, full screen for live demo segment |
| API docs | `http://localhost:8000/docs` ready to show signatures |
| Optional | `demo_ai_agents.py` or `backend/tools/keygen.py` output pre-captured if live keygen is risky |

**Official links** (hand to motion graphics / end card; replace `YOUR_ACTUAL_USERNAME` / `YOUR_ACTUAL_GITHUB_USERNAME` with the real GitHub handle or org before final export):

| Asset | URL / text |
|-------|------------|
| **GitHub repo** | `https://github.com/YOUR_ACTUAL_USERNAME/agentpay` |
| **GitHub profile / handle** | `YOUR_ACTUAL_GITHUB_USERNAME` |
| **Live demo** | `http://agentpay-demo.railway.app` — *if not deployed yet, use an on-screen **Coming soon** card instead of this URL.* |
| **Documentation** | README in repo + OpenAPI at `/docs` on any running backend |

---

## [0:00–0:45] THE PROBLEM — *Narasi kuat*

| Timecode | Section | Edit notes |
|----------|---------|------------|
| `00:00` | Hook + problem | `[CUT TO: title card]` or cold open on abstract motion |
| `00:12` | Problem deepens | Optional `[OVERLAY: "Trustless?"]` |
| `00:25` | Why legacy fails | Punch cuts on each ❌ bullet |
| `00:38` | Bridge to solution | `[CUT TO: title card]` **AgentPay** wordmark |

### ON SCREEN

- Abstract visuals: two AI “nodes,” a question mark between them, then red X over “manual card” and “single company logo.”
- Optional: simple diagram — *Agent A* → *?* → *Agent B*.

### NARRATOR *(word-for-word)*

> Imagine a future where AI agents trade services autonomously.  
> Agent A needs language translation. Agent B provides translation for five dollars.  
> **How do they transact trustlessly** — without a human in the loop, and without trusting each other’s code?
>
> Traditional approaches break down fast.  
> **Manual payment processing** doesn’t scale when millions of agents negotiate in real time.  
> **Centralized payment gateways** become a single point of failure — and a single point of control.  
> There’s **no cryptographic proof** of who authorized what.  
> And there’s **no real escrow** — so either side can get burned.
>
> **Enter AgentPay** — infrastructure built for the agent economy.

### B-roll / text on screen (optional lower third)

- Manual payment ❌  
- Centralized gateways ❌  
- No cryptographic proof ❌  
- No escrow ❌  

**End beat:** Logo or wordmark: **AgentPay** — `[OVERLAY: "Built for autonomous agents"]` (optional, 2s)

---

## [0:45–1:15] THE SOLUTION

| Timecode | Section | Edit notes |
|----------|---------|------------|
| `00:45` | One-liner positioning | `[OVERLAY: "Stripe for AI agents"]` on first VO beat (optional) |
| `00:55` | Five pillars (visual) | Stagger animate pillars; `[OVERLAY: "Ed25519 · Escrow · REST"]` on pillar beat |
| `01:10` | Transition to live | `[CUT TO: terminal]` pre-roll 0.5s black or whip pan |

### ON SCREEN

- Full-screen title: **AgentPay — payments for autonomous agents**
- Bullet checklist animating in (see NARRATOR).

### NARRATOR *(word-for-word)*

> **AgentPay is the Stripe for AI agents.**  
> Any agent — or any automation — can call a **REST API**.  
> Every sensitive action is backed by **Ed25519 signatures**, so you get **non-repudiation**: cryptographically, you can prove who agreed to what.  
> Money moves through an **escrow-style flow**: funds commit when a payment starts, and **settlement** only completes when both sides complete the handshake.  
> It’s **production-grade**: Postgres, Redis, health checks, metrics — not a weekend script.  
> And for operators: **one command** brings the whole stack up.
>
> Let me show you.

### ON SCREEN (pillars)

✅ REST API any agent can call  
✅ Ed25519 signatures (non-repudiation)  
✅ Escrow-based settlement (trustless flow)  
✅ Production-grade infrastructure  
✅ One-command deployment  

---

## [1:15–3:00] LIVE DEMO

| Timecode | Section | Edit notes |
|----------|---------|------------|
| `01:15` | Stack boot | `[CUT TO: terminal]` — typing `./start.sh` |
| `01:22` | Containers rising | Fast montage of `docker compose` lines OK (≤3s) |
| `01:30` | Health check | `[ZOOM IN: "status": "ok"]` in curl JSON |
| `01:35` | Dashboard | `[CUT TO: browser]` localhost:3000 |
| `01:42` | Swagger peek (opt.) | `[CUT TO: browser]` `/docs` — `[OVERLAY: "Full OpenAPI"]` |
| `01:50` | Alice: keypair + register | `[ZOOM IN: public_key]` (blur private) |
| `01:56` | Signed registration | `[OVERLAY: "Cryptographically Verified ✓"]` on 201 response |
| `02:10` | Bob: keypair + register | Match Alice pacing; same overlay on success |
| `02:25` | Payment flow | See substeps A–C below |
| `02:50` | Security demos | Quick cuts; see §6 |

### 1) Bring up the stack

`01:15` — **[CUT TO: terminal]**

**TERMINAL — from repo root**

```bash
./start.sh
```

**Equivalent (explicit)**

```bash
docker compose up --build -d --remove-orphans
```

**Show**

- Four services: **postgres**, **redis**, **backend**, **frontend** (as in your `docker-compose.yml`).
- Wait until backend healthy (~45s first build; faster on repeat).

**TERMINAL — verify**

```bash
curl -s http://localhost:8000/health | jq .
```

**Example response** (highlight `status`) — **`[ZOOM IN: "status": "ok"]`**

```json
{
  "status": "ok"
}
```

**NARRATOR**

> I’m starting the full stack with one script. Postgres, Redis, the FastAPI backend, and the frontend — all on the same Docker network.  
> Health check passes — we’re ready to open the app.

`01:35` — **[CUT TO: browser]**

---

### 2) Dashboard

**ON SCREEN**

- Browser: **http://localhost:3000**
- Swagger (optional cut): **http://localhost:8000/docs**

**NARRATOR**

> Here’s the dashboard. Everything agents do ultimately hits the API under `/api/v1` — and you can inspect every endpoint in Swagger.

---

### 3) Step 1 — Create Agent Alice (translator buyer)

**Story:** Alice buys translation; she needs a keypair and a signed registration.

`01:50` — **[CUT TO: terminal]** · **`[ZOOM IN: public_key line]`** (mask private key in post)

**TERMINAL — generate keys (example using project helper)**

```bash
cd backend && python tools/keygen.py --agent-id alice --balance 100
```

**Show on screen**

- Private key (blur or redact in post if recording for public)
- Public key Base64
- Sample signed `curl` to `POST /api/v1/agents`

**API — register agent (conceptual; values from keygen output)**

`POST /api/v1/agents`

```json
{
  "agent_id": "alice",
  "initial_balance": "100.00",
  "public_key": "<base64-ed25519-public>",
  "timestamp": "2026-05-02T12:00:00.000000+00:00",
  "signature": "<base64-signature>"
}
```

**Response** `201 Created` — highlight `balance`, `agent_id`.  
**`[OVERLAY: "Cryptographically Verified ✓"]`** (1.5–2.5s, sync to “signed request” in VO)

**NARRATOR**

> Alice is our buyer. We generate an Ed25519 keypair — same family of cryptography used in SSH and Git.  
> She registers with a **signed** request: the server stores her public key. From now on, only whoever holds the private key can authorize payments **as Alice**.

---

### 4) Step 2 — Create Agent Bob (translator provider)

`02:10` — **[CUT TO: terminal]** (same framing as Alice for visual consistency)

**TERMINAL**

```bash
python tools/keygen.py --agent-id bob --balance 0
```

**API** — same shape, `agent_id`: `bob`, `initial_balance`: `"0.00"`.

**NARRATOR**

> Bob is the provider — starting balance zero. He registers the same way. Two agents, two keys, one shared ruleset.

---

### 5) Step 3 — Payment flow ($5 translation job)

**Use case:** Alice pays Bob **$5.00** for a translation job (escrow semantics match AgentPay’s transaction model).

`02:25` — **[CUT TO: terminal]** or Swagger try-it-out; keep JSON readable.

#### A) Alice initiates payment

`POST /api/v1/transactions`  
(Signed by **Alice’s** private key — `from_agent` = alice, `to_agent` = bob, unique `nonce`.)

**Request body (illustrative)**

```json
{
  "from_agent": "alice",
  "to_agent": "bob",
  "amount": "5.00",
  "nonce": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2026-05-02T12:01:00.000000+00:00",
  "signature": "<base64>"
}
```

**Response** `201 Created` — show:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "from_agent": "alice",
  "to_agent": "bob",
  "amount": "5.00",
  "status": "INITIATED",
  "created_at": "...",
  "timeout_at": "..."
}
```

**`[ZOOM IN: "status": "INITIATED"]`** · **`[OVERLAY: "Funds escrowed"]`** (optional)

**ON SCREEN — balances**

- `GET /api/v1/agents/alice/balance` → e.g. **95.00** (100 − 5 escrowed)  
- Bob still **0.00** until settlement

**`[ZOOM IN: balance display]`** — Alice **95.00** vs Bob **0.00** (side-by-side or split screen)

**NARRATOR**

> Alice initiates a five-dollar payment to Bob.  
> Status: **INITIATED**. Her balance drops by five — funds are **committed**, not yet Bob’s. That’s escrow protection.

---

#### B) Bob accepts (service request received)

`POST /api/v1/transactions/{txn_id}/accept`  
(Signed by **Bob** — receiver.)

**Request body (illustrative)**

```json
{
  "agent_id": "bob",
  "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
  "nonce": "unique-nonce-for-this-action",
  "timestamp": "2026-05-02T12:01:30.000000+00:00",
  "signature": "<base64>"
}
```

**Response** — `status`: **PENDING** — **`[ZOOM IN: "PENDING"]`**

**NARRATOR**

> Bob accepts. Status moves to **PENDING** — he’s committed to deliver; Alice hasn’t finalized yet.

---

#### C) Alice confirms (translation received, quality verified)

`POST /api/v1/transactions/{txn_id}/confirm`  
(Signed by **Alice** — sender.)

**Response** — `status`: **SETTLED** (and timestamps if exposed) — **`[ZOOM IN: "SETTLED"]`** · **`[OVERLAY: "Cryptographically Verified ✓"]`** (settlement beat)

**ON SCREEN — final balances**

- Alice: **95.00** (100 − 5 spent)  
- Bob: **5.00** (received)

**`[ZOOM IN: balance display]`** — hold **Alice 95.00 | Bob 5.00** (lower third or full-width numeric)

**NARRATOR**

> Alice confirms she received the translation.  
> Status: **SETTLED**. Bob’s balance goes from zero to five. Alice’s balance stays at ninety-five — five dollars moved, with cryptographic proof at every step.

---

### 6) Step 4 — Security demo (quick cuts)

`02:50` — **[CUT TO: terminal]** — rapid sequence (≤25s total); keep HTTP status codes large in caption layer.

**A) Unsigned / wrong signature**

Send `POST /api/v1/transactions` with garbage `signature` or tampered body.

**Expected:** `401` — invalid signature

```json
{
  "detail": "Tanda tidak valid"
}
```

*(Exact message may vary; emphasize **401**.)*  
**`[OVERLAY: "Cryptographically Verified ✓"]`** *(ironic beat: “verification failed — signature required”)* or use **`[OVERLAY: "Invalid signature — rejected"]`**

**NARRATOR**

> Try to submit a transaction without a valid signature — **rejected**. The server verifies Ed25519 on every state-changing call.

---

**B) Replay — reuse nonce**

Repeat the **same** `nonce` on a new transaction.

**Expected:** `400` — nonce replay

**NARRATOR**

> Replay the same nonce — **rejected**. One-time use stops replay attacks.

---

**C) Insufficient balance**

Alice tries to pay more than her balance.

**Expected:** `409` or balance-related error (per API; show status code on screen)

**NARRATOR**

> Insufficient balance — **rejected** before any money moves. The database enforces this under locking — no optimistic double-spend.

**NARRATOR (closing this segment)**

> Every step is auditable: who signed, when, and what state the transaction reached.

---

## [3:00–3:45] TECHNICAL HIGHLIGHTS

| Timecode | Section | Edit notes |
|----------|---------|------------|
| `03:00` | Stack + DB | `[CUT TO: title card]` or architecture still; `[OVERLAY: "FastAPI · Postgres · Redis"]` |
| `03:20` | Crypto + state machine | Diagram animate; `[OVERLAY: "Ed25519 + state machine"]` |
| `03:35` | Quality bar | `[OVERLAY: "20+ tests · ≥84% coverage"]` |

### ON SCREEN

- Architecture diagram (from README): browser → nginx → backend → Postgres / Redis  
- Optional: snippet of transaction state **INITIATED → PENDING → CONFIRMED / SETTLED** path as in your code

### NARRATOR *(word-for-word)*

> Under the hood, AgentPay is a **FastAPI** backend — async, high throughput.  
> **PostgreSQL** holds agents, balances, and transactions; critical sections use **row-level locking** so concurrent agents don’t corrupt state.  
> **Ed25519** signatures are the same primitive family people trust in SSH and Git — small keys, fast verification.  
> Transactions follow a strict **state machine**: initiated, pending, then settled or rolled back — no ambiguous in-between states for money.  
> We ship **twenty-plus automated tests** and hold the bar at **eighty-four percent coverage minimum** for the backend — so regressions get caught before production.  
> In typical conditions you see **sub-one-hundred-millisecond** API latency on a laptop-class stack.  
> **Production-ready on day one** isn’t a slogan — it’s the baseline we built to.

### Optional on-screen bullets

- FastAPI (async)  
- PostgreSQL + row locks  
- Ed25519  
- Explicit transaction state machine  
- 20+ tests · ≥84% coverage target  
- Sub-100 ms typical API latency  

---

## [3:45–4:30] PHASE 2 READINESS — *The Bazaar / NandaHack*

| Timecode | Section | Edit notes |
|----------|---------|------------|
| `03:45` | Map requirements to product | `[CUT TO: browser]` or b-roll; `[OVERLAY: "The Bazaar — Phase 2"]` |
| `04:15` | “Any agent” | Three-way split: Claude / GPT / curl — **`[OVERLAY: "Just REST"]`** |

### NARRATOR *(word-for-word)*

> We’re building for **Phase Two — the Bazaar**: an economy where agents discover each other, prove identity, and **settle** payments.  
> AgentPay delivers three things that bazaar-style problems ask for:  
> **Economic infrastructure** — balances and settlement, not just chat.  
> **Identity verification** — not government ID, but **cryptographic** identity: your agent is your keypair.  
> And a **settlement mechanism** — escrow plus an explicit state machine, so “paid” means something enforceable in software.  
> **Any AI agent** — Claude, GPT, a small open-source model, or a cron job — can integrate with **plain HTTP** and JSON.  
> **No vendor SDK required.** No lock-in integration layer. **Just REST.**

### ON SCREEN

✅ Economic infrastructure (payments)  
✅ Identity verification (Ed25519)  
✅ Settlement (escrow + state machine)  
✅ Claude · GPT · custom LLMs · **HTTP**  

---

## [4:30–5:00] CALL TO ACTION

| Timecode | Section | Edit notes |
|----------|---------|------------|
| `04:30` | Recap + links | `[CUT TO: title card]` — show URLs as motion type |
| `04:40` | QR + handles | On-screen: GitHub URL + optional QR to `https://github.com/YOUR_ACTUAL_USERNAME/agentpay` |
| `04:50` | Final line | Hold logo; fade VO under 1s |

### ON SCREEN

- **GitHub:** `https://github.com/YOUR_ACTUAL_USERNAME/agentpay` + QR (optional)  
- **Live demo:** `http://agentpay-demo.railway.app` — *or **Coming soon** full card if not deployed*  
- **Docs:** “Full API — README & `/docs`”

### NARRATOR *(word-for-word)*

> **AgentPay** enables the autonomous agent economy — not as a slide, but as **running code**.  
> **GitHub:** `https://github.com/YOUR_ACTUAL_USERNAME/agentpay`  
> **Live demo:** `http://agentpay-demo.railway.app` — or **Coming soon** until we’re live in production.  
> **Documentation:** full API reference in the README, and interactive **OpenAPI** at `/docs` on any deployment.  
>
> This is **infrastructure**. This is **foundational**.  
> **This is how agents will transact in twenty-twenty-six.**

**End card:** Logo + `https://github.com/YOUR_ACTUAL_USERNAME/agentpay` + **`http://agentpay-demo.railway.app`** (or **Coming soon**) + **Thank you**

`04:52` — **[CUT TO: black]** or outro sting (0.5s)

---

## Appendix A — Quick reference: endpoints to film

| Action | Method | Path |
|--------|--------|------|
| Health | GET | `/health` |
| Create agent | POST | `/api/v1/agents` |
| Balance | GET | `/api/v1/agents/{agent_id}/balance` |
| Create payment | POST | `/api/v1/transactions` |
| Accept | POST | `/api/v1/transactions/{id}/accept` |
| Confirm | POST | `/api/v1/transactions/{id}/confirm` |
| List (filter) | GET | `/api/v1/transactions?agent_id=alice` |
| OpenAPI | GET | `/docs` |

---

## Appendix B — Optional: AI agent demo clip (30–45s insert)

If you want a **Claude** angle without manual curl:

**TERMINAL**

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python demo_ai_agents.py
```

**VO line:** *“Here two Claude agents negotiate, pay, and settle through the same AgentPay API — autonomously.”*

---

## Appendix C — Editing notes

- **Pacing:** Problem 45s → Solution 30s → Live demo 105s is tight; trim security to one example if over time.  
- **Music:** None under narration; subtle bed under title cards only.  
- **Captions:** Burn in API status codes (`201`, `401`, `INITIATED`, `SETTLED`) for viewers on mute.  
- **Redaction:** Never leave private keys on screen in public cuts.  
- **Placeholders:** Search project for `YOUR_ACTUAL_USERNAME` and `YOUR_ACTUAL_GITHUB_USERNAME` before master export; confirm Railway URL or swap to **Coming soon**.  
- **Marker summary:** Use `[CUT TO: terminal]` / `[CUT TO: browser]` on every major scene change in LIVE DEMO; stack `[ZOOM IN: balance display]` on all final balance shots; reserve `[OVERLAY: "Cryptographically Verified ✓"]` for successful signed registration and SETTLED confirmation (and pair with “rejected” overlay for 401).

---

## Appendix D — Master link sheet (for editor / motion)

| Use | Value |
|-----|--------|
| Repository | `https://github.com/YOUR_ACTUAL_USERNAME/agentpay` |
| GitHub handle (VO + lower third) | `YOUR_ACTUAL_GITHUB_USERNAME` |
| Live demo | `http://agentpay-demo.railway.app` *(alt: on-screen **Coming soon**)* |
| Local dashboard (recording) | `http://localhost:3000` |
| Swagger (recording) | `http://localhost:8000/docs` |

---

*Document: DEMO_SCRIPT_V2.md — AgentPay demo narrative for video production.*
