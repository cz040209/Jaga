# FraudShield — Project Brief

This file describes the system to build. Read it fully before planning or writing code. The tech stack is specified separately in the **Tech Stack** section at the end (to be filled in).

---

## 1. What we are building

**FraudShield** is a real-time fraud and scam detection platform for a **mock digital bank**, focused on the **Malaysian online scam problem**.

It has three parts that work together:

1. **A mock bank** (customer-facing, phone-first web app, also runnable as a Telegram Mini App). Real people register, log in, add payees, transfer money and pay merchants. Money is fake, but accounts, balances and the ledger are real inside the system.
2. **A real-time fraud engine** that scores every event (login, transfer, payment, payee change) the moment it happens and decides **APPROVE / STEP-UP / HOLD / BLOCK** in under 50 ms.
3. **A fraud operations dashboard** (desktop, for analysts and the risk team) with a live transaction feed, case management, AI investigation, rule management and model monitoring.

AI is used in two ways:
- **Machine learning** inside the real-time decision path (scoring).
- **Generative AI (LLM)** around the decision path: investigating cases, explaining decisions, talking to customers, writing rules, red-teaming. The LLM is **never** in the < 50 ms decision path.

This is a portfolio-grade project meant to look and behave like a real product, runnable entirely on one laptop.

---

## 2. Core principles (non-negotiable)

1. **No fake data shown in the product.** There is no background script generating fake transactions. Every transaction in the app comes from a real person using the mock bank. Fraud is *acted out* by people (or by the sandboxed AI red-team agent in Phase 3), not generated. Public datasets (e.g. PaySim, IEEE-CIS) may be used **only offline to pre-train ML models**, never displayed as activity.
2. **Runs fully on a laptop.** All services run locally via Docker Compose. No production server required. The only external paid dependency is the LLM API.
3. **Works without an LLM API key.** Every LLM feature must have a fallback (template text or feature disabled with a clear message) so the system runs offline.
4. **The LLM is never in the real-time path.** Real-time decisions use rules + ML only. LLM work runs asynchronously (background jobs) or on user request.
5. **Human in the loop.** AI recommends; analysts decide on held/blocked cases. Every decision is logged with its reasons for audit.
6. **Explainable decisions.** Every score comes with top reasons (rule hits, feature contributions). Customers get a plain-language explanation.
7. **Pluggable detectors.** Each detector is an independent module with a common interface (input: event + features; output: score 0–100 + reasons). Adding a new detector (AML, merchant risk, credit scoring) must not require changing the pipeline.
8. **Channel-agnostic notifications.** One `notify(user, message)` interface with an adapter per channel (Web Push, Telegram, email, in-app SMS inbox, Slack/Discord, WhatsApp later).
9. **Professional UI.** Polished, production-quality frontend. Not Streamlit, not a prototype look.

---

## 3. Users

| User | Interface | Goals |
|---|---|---|
| **Customer** | Mock bank app (PWA / Telegram Mini App) + Telegram bot | Bank normally; get warned or protected from scams; check suspicious messages; freeze account fast |
| **Fraud analyst** | Ops dashboard | Review held/blocked transactions, investigate cases, approve/reject, label fraud |
| **Risk manager** | Ops dashboard | Write and tune rules, set thresholds, see business impact, monitor models |
| **Attacker / red-teamer** (demo role) | Mock bank app + Scam Arena | Try to steal money without being caught (for demos and to generate training data) |

---

## 4. End-to-end flow

### Real-time path (customer is waiting, total < 50 ms)

1. **Event** — customer action in the mock bank (login, transfer, payment, add payee, change password/device). The frontend also sends device fingerprint and behavioural signals (typing rhythm, time from login to confirm, paste into account-number field, etc.).
2. **Ingest** (~2 ms) — API validates the event, assigns an ID and timestamp, and publishes it to the event stream.
3. **Enrich** (~5 ms) — feature store lookup: transaction counts and amounts over 5 min / 1 h / 24 h, amount vs. the user's normal, known devices, saved payees, usual locations and hours, payee account age, blacklists / mule list.
4. **Detect** (~20 ms, detectors in parallel) — each detector returns score + reasons:
   - Rules engine (risk-team rules in YAML)
   - Fraud ML classifier
   - Per-user anomaly model
   - Account-takeover detector (new device, impossible travel, recent password reset, SIM change)
   - Scam / coaching detector (new payee + large amount + odd hour + rushed session + draining balance)
   - Mule graph detector (accounts receiving from many unrelated senders and paying out quickly)
5. **Decide** (~3 ms) — blend scores into one risk score 0–100 and apply thresholds (configurable):
   - **< 40 APPROVE**
   - **40–69 STEP-UP** (OTP or interactive scam check)
   - **70–89 HOLD** (cooling-off delay + warning to customer, case opened)
   - **≥ 90 BLOCK** (transaction rejected, account protective freeze, case opened)
   
   Response returns to the app immediately with the decision and customer-facing reason.

### Async path (seconds, after the customer has an answer)

6. **Act & investigate** — persist event, features, scores and reasons; create/merge cases for HOLD/BLOCK; run the AI case investigator; push to the live dashboard; notify the customer ("Did you make this transfer?" with Yes / No — "No" triggers the kill switch).
7. **Learn** — analyst labels (fraud / not fraud) and customer replies become training labels → retrain → shadow-test new model vs. current → promote if better. Drift monitoring alerts when model behaviour changes.

---

## 5. Mock bank (customer app) — features

- Register / onboarding, log in (device recognised or flagged as new)
- Home: balance, recent activity
- Add payee (with **mule account check** before saving, similar to Malaysia's PDRM "Semak Mule")
- Transfer: choose payee → amount → review → decision (approve / OTP / scam check / hold / block)
- Pay merchant / QR pay
- In-app **SMS inbox** (simulated, for OTPs)
- Notifications
- **Kill switch**: one tap to freeze the account immediately
- **Cooling-off period** for new devices and newly added payees before large transfers
- **Interactive scam check** before a risky transfer is released ("Is someone on the phone telling you to move this money? Did they say they are police / bank / LHDN?") — answers feed back into the risk score
- **"Why was my transfer held?"** plain-language explanation
- **Report scam** — generates a pre-filled report for the National Scam Response Centre (997)
- Every new account starts with a fake balance (e.g. RM 10,000). Transfers move money between real accounts in the system using a double-entry ledger.
- Phone-first, installable (PWA). Must also run inside Telegram as a Mini App.
- Multiple people on different devices (phone over local Wi-Fi, laptop) must be able to use it at the same time.

---

## 6. Telegram bot — features

- Live fraud alerts with inline buttons: "✅ It was me" / "🚫 Not me — freeze my account"
- `FREEZE` command → kill switch
- **Scam message checker**: user forwards a suspicious SMS / WhatsApp text or screenshot → AI says whether it is a scam and why
- OTP delivery for step-up
- Daily summary ("3 transactions today, 0 suspicious")
- Opens the mock bank as a Telegram Mini App
- Supports English, Malay and Chinese

---

## 7. Fraud ops dashboard — features

- **Live feed** of transactions with risk scores; high-risk rows highlighted in real time
- **Case queue**: HOLD/BLOCK cases, grouped per customer / campaign, sortable and filterable
- **Case detail**: timeline, detector scores, top reasons (SHAP chart), AI investigator summary + recommended action, related accounts, Approve / Reject / Mark fraud buttons
- **Mule network view**: interactive graph of money flows, with an AI narration of the pattern
- **Chat with your data**: natural-language questions answered via validated, read-only SQL
- **Rules management**: list / enable / disable rules; write a rule in plain English → AI converts it to YAML → back-test against past events ("would have caught X frauds, held Y genuine transfers") → save
- **Business impact**: "RM prevented today", false-positive rate, customers inconvenienced
- **Threshold trade-off simulator**: slider showing fraud caught vs. genuine customers inconvenienced
- **Model monitoring**: score distribution, approval rate, drift alerts, shadow-test comparison, model versions
- **Scam Arena** leaderboard (see below)
- Analyst alerts also go to Slack or Discord
- Dark and light theme; desktop-first, data-dense layout

---

## 8. Scam Arena (signature feature)

A red team vs. blue team game:
- Anyone can play the attacker: try to move money out of a designated victim account without being caught.
- The fraud engine tries to stop them live.
- A leaderboard ranks attackers by money successfully moved.
- Every successful bypass is flagged as a missed fraud and becomes training data / a rule suggestion, so the system learns from each attack.

---

## 9. AI feature catalogue (27 features)

### Generative AI / LLM (17)

| # | Feature | Who | Phase |
|---|---|---|---|
| 1 | Scam message checker (text + screenshot) | Customer (Telegram) | MVP |
| 2 | "Why was my transfer held?" explainer | Customer | MVP |
| 3 | Interactive scam interview before releasing a risky transfer | Customer | 2 |
| 4 | Support assistant (unfreeze, declined payment, how to report) | Customer | Extra |
| 5 | Multilingual replies (EN / BM / ZH) | Customer | 2 |
| 6 | AI case investigator (summary + recommended action, uses tools to fetch history) | Analyst | MVP |
| 7 | Chat with your data (NL → validated read-only SQL) | Analyst | 3 |
| 8 | Mule ring narrator | Analyst | 2 |
| 9 | Auto-draft suspicious transaction / police reports | Analyst | Extra |
| 10 | Case triage and alert grouping | Analyst | Extra |
| 11 | Rules in plain English → YAML + back-test | Risk team | 2 |
| 12 | Rule review (overlaps, conflicts, stale rules) | Risk team | Extra |
| 13 | Daily scam trend briefing | Risk team | Extra |
| 14 | AI scammer role-play in a sandbox chat (tests coaching detection) | Testing | 3 |
| 15 | Automated red-team agent (finds rule gaps, feeds Scam Arena) | Testing | 3 |
| 16 | Label assistant (analyst notes + customer replies → labels) | Feedback loop | 3 |
| 17 | Feature suggestions from missed fraud | Feedback loop | Extra |

### Machine learning (10)

| # | Feature | Phase |
|---|---|---|
| 18 | Fraud classifier (gradient boosting) | 2 |
| 19 | Per-user anomaly detection | MVP |
| 20 | Account-takeover detector | MVP |
| 21 | Scam / coaching pattern detector | MVP |
| 22 | Mule network detection (graph) | 2 |
| 23 | Behavioural biometrics (typing rhythm, session speed) | Extra |
| 24 | Explainability (SHAP reasons) | 2 |
| 25 | Risk score blending + decision thresholds | MVP |
| 26 | Model drift monitoring | 3 |
| 27 | Shadow testing / replay of new models | 3 |

**ML cold start:** with few real users there is little history. Start with rules + per-user anomaly detection (work from day one), pre-train the classifier offline on a public dataset, then improve it with analyst labels from real usage.

**LLM cost control:** call the LLM only for HOLD/BLOCK cases, scam checks and chat — never per transaction. Use prompt caching for fixed instructions/policies. Template fallback when no API key.

---

## 10. Core data entities (initial)

- **User / Customer** — profile, language, Telegram chat ID, status (active / frozen)
- **Device** — fingerprint, first seen, last seen, trusted flag
- **Session / Login event** — device, IP, location, behavioural signals
- **Account** — balance (derived from ledger), currency MYR
- **Payee** — owner, target account, created_at (for cooling-off), mule-check result
- **Transaction** — type, amount, from, to, channel, status, decision, risk score
- **Ledger entry** — double-entry debit/credit lines per transaction
- **Detector result** — per event per detector: score, reasons
- **Decision** — final score, action, top reasons, latency
- **Case** — linked events, status, assignee, AI summary, resolution, label
- **Label** — fraud / not fraud, source (analyst, customer reply, arena)
- **Rule** — YAML definition, author, enabled, version, back-test results
- **Model version** — metrics, status (shadow / active / retired)
- **Notification** — channel, template, delivery status
- **Staff user** — analyst / risk manager / admin roles
- **Arena attempt** — attacker, target, amount moved, detected or not

---

## 11. Non-functional requirements

- **Latency:** real-time decision p95 < 50 ms on a laptop; prove it with a load test.
- **Reliability:** events are queued durably; a crashed worker must not lose events.
- **Auditability:** every decision stores input features, detector outputs, final score, reasons and model/rule versions.
- **Security:** hashed passwords, short-lived access tokens + refresh tokens, separate staff vs. customer auth, role-based access on the dashboard, read-only DB role for any LLM-generated SQL, secrets only in `.env` (never committed).
- **Privacy:** minimal personal data; mask account numbers in UI and in LLM prompts where possible.
- **One-command startup:** `docker compose up` brings up the whole system.
- **Testability:** automated end-to-end tests that replay fraud scenarios (scam transfer, account takeover, mule ring, card testing) and assert the expected decisions.

---

## 12. Fraud scenarios the system must catch (acceptance tests)

1. **Authorised push-payment scam** — victim coached by phone; new payee added minutes ago; large amount; late night; fast session; balance nearly drained → HOLD + scam check.
2. **Account takeover** — login from a new device / far location, password change, then transfer out → STEP-UP or BLOCK.
3. **Mule ring** — several accounts receive from many unrelated senders and forward quickly → mule detector flags; graph shows the ring.
4. **Card testing / micro-payments** — many tiny payments in a short window → velocity rules flag.
5. **Normal behaviour** — a regular user making usual-sized transfers to saved payees → APPROVE with low false-positive rate.

---

## 13. Build phases

| Phase | Scope |
|---|---|
| **1 — Mock bank** | Auth, accounts, double-entry ledger, payees, transfers, in-app SMS inbox, customer UI, Docker Compose setup |
| **2 — Real-time engine** | Event stream, feature store, rules engine, anomaly + ATO + scam detectors, decision engine, step-up / hold / block flows, kill switch, cooling-off |
| **3 — Ops dashboard** | Live feed, cases, case detail, approve/reject, labels, business-impact counter |
| **4 — AI (MVP set)** | AI case investigator, "why was I held", Telegram bot with alerts + scam message checker |
| **5 — Portfolio-grade** | Fraud classifier + SHAP, mule graph + narrator, rules in plain English + back-test, interactive scam interview, multilingual, Telegram Mini App, Scam Arena |
| **6 — Standout** | Chat with your data, red-team agent, AI scammer sandbox, label assistant, drift monitoring, shadow testing, observability |

Deliver each phase as a working, runnable increment before starting the next.

---

## 14. Out of scope

- Real money, real bank or payment-network connections
- Real SMS sending (OTP is simulated in-app / via Telegram)
- Production cloud deployment (may be added later)
- Face / emotion analysis

---

## 15. Repository state

This folder contains leftovers from an abandoned earlier setup: a git repo with no commits, a partially created Python `.venv`, and empty folders `app/`, `data/`, `models/`, `scripts/`, `static/`. They follow an older single-app layout. Replace them with the structure that fits the tech stack below.

---

## 16. Tech Stack

### 16.1 Frontend — customer bank app + fraud ops dashboard (one Next.js project)

| Purpose | Tech |
|---|---|
| Framework | **Next.js 15** (App Router) + **TypeScript** |
| Styling | **Tailwind CSS** |
| UI components | **shadcn/ui** (built on Radix) |
| Animations | **Framer Motion** |
| Tables | **TanStack Table** |
| Charts | **Recharts** |
| Mule network graph | **React Flow** |
| API calls and caching | **TanStack Query** |
| Forms and validation | **React Hook Form** + **Zod** |
| Live updates | **WebSocket** |
| Mobile app feel | **PWA** (installable to phone home screen) |
| Device fingerprint | **FingerprintJS** (open-source) |
| Behavioural signals | Custom JS (typing rhythm, time on screen, paste detection) |
| Telegram Mini App | **Telegram Web Apps SDK** (bank app runs inside Telegram) |

Route groups: `(bank)` for the phone-first customer app, `(ops)` for the desktop analyst dashboard.

### 16.2 Backend

| Purpose | Tech |
|---|---|
| API framework | **Python FastAPI** + **Pydantic v2** |
| ORM and migrations | **SQLAlchemy 2.0** + **Alembic** |
| Customer auth | **JWT** (short-lived access + refresh tokens) + **bcrypt** |
| Staff auth | Separate staff JWT login with roles (analyst / risk manager / admin); **Keycloak** SSO optional |
| Step-up / OTP | Simulated in-app SMS inbox + Telegram OTP |
| Scoring worker | Separate Python process consuming the event stream |
| Background jobs | **ARQ** (Redis-based task queue) for LLM calls, reports, retraining |
| Rules engine | **YAML** rules evaluated in Python |
| IP to location | **MaxMind GeoLite2** |
| Device parsing | **ua-parser** |
| Ledger | Double-entry ledger in Postgres (fake money, real accounting) |

### 16.3 Data

| Purpose | Tech |
|---|---|
| Main database | **PostgreSQL 16** |
| Vector search | **pgvector** (scam knowledge base, policies) |
| Event stream | **Redis Streams** (behind an interface; **Redpanda** as a Kafka-compatible option via `BUS=redpanda`) |
| Feature store / cache | **Redis** (hashes + sorted sets for time windows) |
| Scam Arena leaderboard | Redis sorted sets |
| Model artifacts | Local volume, tracked by MLflow |

### 16.4 Machine learning

| Purpose | Tech |
|---|---|
| Fraud classifier | **XGBoost** / **LightGBM** |
| Anomaly detection | **scikit-learn Isolation Forest** |
| Graph / mule detection | **NetworkX** (Neo4j optional later) |
| Explainability | **SHAP** |
| Experiment tracking + model registry | **MLflow** |
| Drift monitoring | **Evidently** |
| Data handling | **pandas** / **Polars**, **NumPy** |
| Notebooks | **Jupyter** |
| Offline pre-training data | **PaySim** / **IEEE-CIS** public datasets (training only, never shown in the app), then analyst labels |

### 16.5 Generative AI (LLM)

| Purpose | Tech |
|---|---|
| LLM | **Claude API**, model `claude-opus-5-5` |
| SDK | **`anthropic`** Python SDK (async client) |
| Screenshot scam checking | Claude vision (image input) |
| Structured output (rules, labels, case JSON) | Claude structured outputs + Pydantic validation |
| Agents (case investigator, red-team agent) | Claude tool use with our own tools (query DB, fetch history, run back-test) |
| Embeddings (scam similarity, policy search) | **sentence-transformers**, multilingual model, runs locally |
| Safe "chat with your data" | Read-only Postgres role + **sqlglot** validation of generated SQL |
| Cost control | Prompt caching; LLM only for HOLD/BLOCK cases, scam checks and chat; template fallback without API key |

Before writing Claude API code, check the current Anthropic SDK docs for exact parameters. Do not rely on memory.

### 16.6 Messaging and notifications

| Purpose | Tech |
|---|---|
| Telegram bot (alerts, kill switch, scam checker) | **aiogram 3** (async), long polling in development |
| Phone notifications from the PWA | **Web Push** (VAPID) via **pywebpush** |
| Email (development) | **Mailpit** |
| Email (later) | **Resend** (free tier) |
| Analyst alerts | **Slack** or **Discord** webhooks |
| WhatsApp (later) | Meta **WhatsApp Cloud API** with a test number |
| Single interface | Own `notify()` layer with one adapter per channel |

### 16.7 Infrastructure (all local)

| Purpose | Tech |
|---|---|
| Run everything | **Docker Compose** (`docker compose up`) |
| HTTPS for Telegram Mini App / phone testing | **Cloudflare Tunnel** (`cloudflared`) or **ngrok** free plan |
| Reverse proxy (optional) | **Caddy** |
| Python packages | **uv** |
| JS packages | **pnpm** |
| Secrets | `.env` files (never committed; provide `.env.example`) |

### 16.8 Quality and testing

| Purpose | Tech |
|---|---|
| Backend tests | **pytest** + **httpx** |
| End-to-end / fraud scenario replay | **Playwright** |
| Load testing (prove p95 < 50 ms) | **Locust** |
| Python lint / types | **Ruff** + **mypy** |
| JS lint / format | **ESLint** + **Prettier** |
| CI | **GitHub Actions** |

### 16.9 Observability (Phase 6)

| Purpose | Tech |
|---|---|
| Metrics | **Prometheus** + **Grafana** |
| Tracing | **OpenTelemetry** |
| Error tracking | **Sentry** (free tier) |

### 16.10 Suggested repository layout

```
fraud-shield/
├── CLAUDE.md
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── pyproject.toml
│   ├── alembic/
│   └── app/
│       ├── api/            # FastAPI routers: auth, accounts, transfers, payees, cases, rules, ws
│       ├── core/           # config, security, db session
│       ├── models/         # SQLAlchemy models
│       ├── schemas/        # Pydantic schemas
│       ├── ledger/         # double-entry money movement
│       ├── bus/            # event stream interface (Redis Streams / Redpanda adapters)
│       ├── features/       # feature store
│       ├── detectors/      # one module per detector, common interface
│       ├── decision/       # score blending, thresholds, reasons
│       ├── cases/          # case management
│       ├── ai/             # LLM features: investigator, explainer, scam checker, rules writer
│       ├── notify/         # notify() + channel adapters
│       ├── telegram/       # aiogram bot
│       ├── jobs/           # ARQ background jobs
│       └── worker.py       # stream consumer / scoring worker
├── ml/                     # training scripts, notebooks, datasets (gitignored)
├── rules/                  # YAML rules
├── web/                    # Next.js app: app/(bank), app/(ops)
└── tests/                  # e2e fraud scenarios (Playwright), load tests (Locust)
```

### 16.11 Laptop footprint

| Setup | Containers | Approx. RAM |
|---|---|---|
| MVP | Postgres, Redis, API, worker, web, Mailpit | ~1.5 GB |
| Full | + MLflow, Redpanda, Keycloak, Prometheus, Grafana | ~3.5–4 GB |
