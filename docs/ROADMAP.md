# Roadmap

Eight delivery stages. Each stage ends with a **review gate**: the stage is shown, tests are green,
and the next stage starts only after approval. Every stage keeps earlier stages working — that is
part of its definition of done.

Legend: ✅ done · 🔄 in progress · ⬜ planned

---

## Stage 0 — Architecture & contracts ✅

**Why:** agree on the shape of the system before writing code; wrong boundaries are the most
expensive thing to fix later.

**Deliverables**

- `docs/ARCHITECTURE.md` — context, containers, layering rule, ports, pipelines, scheduling, failure
  taxonomy, compliance, scaling path, end-to-end sequence.
- `docs/DATABASE.md` — ER diagram, 12 tables, enums, indexes, dedup keys, retention, migration policy.
- `docs/ROADMAP.md` — this file.
- `docs/adr/0001–0004` — monorepo layering, Celery over APScheduler, canonical vacancy with
  provenance, profile attribute storage.
- `README.md` — project pitch and map of the repository.

**Exit criteria:** schema covers every feature in the brief; data flow answers "what happens between
an HTTP response from hh.ru and a Telegram message".

---

## Stage 1 — Foundation ✅

**Why:** a service is only as good as its wiring: settings, logging, sessions, migrations and a
reproducible local environment. Doing this first makes every later stage testable.

**Scope**

- Monorepo skeleton (`backend/`, `frontend/`, `docs/`, `infra/`), Python packaging via
  `pyproject.toml`, `ruff`, `mypy`, `pytest` configuration.
- `core/config.py` (`pydantic-settings`, `.env`), `core/logging.py` (`structlog` JSON/console),
  `core/exceptions.py`.
- Async engine/session (`asyncpg`), `Base` with naming convention, all 12 ORM models, enums in
  `domain/enums.py`.
- Alembic: initial migration + taxonomy/source seed data migration.
- Health endpoints `/health/live`, `/health/ready`.
- `docker-compose.yml` foundation: `postgres`, `redis`, `api`; multi-stage `backend/Dockerfile`
  (non-root, healthcheck); `.env.example`; `Makefile`.
- CI skeleton: lint + type-check + tests.

**Tests:** settings validation, model constraints (unique fingerprint, cascades), migration
round-trip, health endpoints.

**Exit criteria:** `docker compose up postgres redis` + `alembic upgrade head` + `pytest` green;
`/health/ready` reports DB and Redis.

> Verified against a local PostgreSQL 16 in the development sandbox (the Docker daemon was not
> reachable there). Migration up/down, `alembic check`, and all model/seed tests were executed;
> `docker compose config` validates, but `docker compose up` is re-checked at Stage 5 when the
> worker and beat join the stack.

---

## Stage 2 — Collection & normalization ✅

**Why:** this is the data engine. Everything downstream is only as good as what lands in
`vacancies`.

**Scope**

- Shared async HTTP client: timeouts, connection limits, retries with jittered exponential backoff,
  `Retry-After`, descriptive `User-Agent`.
- `BaseCollector` (pagination, rate limit, logging, `collector_runs` accounting) + `VacancySource`
  port + registry.
- Adapters: hh.ru, RemoteOK, Remotive, Arbeitnow, WeWorkRemotely RSS.
- `normalization/`: `clean_html`, `normalize_company`, `parse_salary`, `detect_seniority`,
  `detect_work_format`, `detect_language`, `extract_technologies`, `fingerprint`.
- `technologies.yml` taxonomy (~120 entries with aliases) + loader/compiler (one regex, longest alias
  first, word boundaries).
- `IngestService` with two-level dedup, company get-or-create, technology upsert.
- CLI `python -m app.cli collect <source>` for manual runs.

**Tests:** golden-file mapping tests per source (`respx` mocked HTTP), parser table tests (salary /
seniority / format / language), alias-matching edge cases (`C++` vs `C`, `Go` vs `Google`), dedup
integration tests against PostgreSQL.

**Exit criteria:** two consecutive collection runs insert 0 duplicates; a forced 500 from a source is
retried and recorded as `failed` without touching other sources.

> Verified live: RemoteOK 99 fetched → 99 created, then 99 duplicates on the second run; Remotive
> 13, Arbeitnow 300 (1 cross-source update), WeWorkRemotely 25 (1 duplicate, 1 update). hh.ru
> answered `403 Forbidden` from the development network (geo restriction) — the failed run is
> recorded with the error text, and the other sources were unaffected.

---

## Stage 3 — Read API ✅

**Why:** the API is the contract for the dashboard and for manual exploration; it also proves the
schema is queryable.

**Scope**

- Repositories: vacancies (filters/sort/pagination), companies, technologies, stats, profile.
- Pydantic schemas: request/response models, `Page[T]`, filter objects, OpenAPI examples.
- Endpoints: `GET /api/v1/jobs`, `GET /api/v1/jobs/{id}`, `GET /api/v1/companies`,
  `GET /api/v1/technologies`, `GET /api/v1/stats`, `POST|PUT /api/v1/profile`.
- Filtering (q, source, company, technology, seniority, work format, salary floor, match score,
  status, date range), sorting whitelist, offset pagination with total count.
- Error handling (uniform problem responses), request-ID middleware, Redis stats cache.

**Tests:** integration tests on a real PostgreSQL (savepoints), pagination/filter/sort matrix,
validation errors, 404/422 shapes, OpenAPI schema snapshot.

**Exit criteria:** `/docs` is usable end-to-end against seeded data; query plans for the feed use
indexes (checked with `EXPLAIN`).

> Verified: 25 API integration tests cover pagination, every filter, sorting, 404/422 problem
> responses, the profile lifecycle and stats shape. Statistics are cached for 60 s and degrade to a
> direct query when Redis is unavailable.

---

## Stage 4 — AI layer & profile ⬜

**Why:** the differentiator of the project. It must be structured, cheap, testable and replaceable.

**Scope**

- `ports/ai_provider.py`, `AIAnalysisResult` schema, prompt builder + prompt `v1`.
- `MockAIProvider` — deterministic heuristic scorer (skills overlap, seniority, salary, format)
  usable in production demo mode.
- `OpenAIProvider` — JSON-schema structured output, timeout, retry, token/cost accounting.
- `AnalysisService`: hard prefilters, cache lookup, validation, one repair attempt, degraded fallback,
  persistence to `ai_analyses` + `user_vacancies`.
- `POST /api/v1/jobs/{id}/analyze`, `GET /api/v1/jobs/{id}/analysis`, `GET /api/v1/profile`.
- AI budget guard (`AI_DAILY_BUDGET_USD`) and per-run cap.

**Tests:** mock provider determinism, schema validation, invalid-JSON repair path, degraded fallback,
prompt snapshot, budget rejection, endpoint contracts.

**Exit criteria:** `AI_PROVIDER=mock` produces sensible scores offline; switching to OpenAI requires
only env changes; no AI call happens for a vacancy that fails hard filters.

---

## Stage 5 — Automation (Celery) ⬜

**Why:** a monitor that must be run by hand is not a monitor.

**Scope**

- Celery app, queues, routing, `acks_late`, prefetch, visibility timeout.
- Tasks: `collect_source`, `collect_all_sources`, `analyze_new_vacancies`, `analyze_vacancy`,
  `send_pending_notifications`, `refresh_stats_cache`, `deactivate_stale_vacancies`.
- Beat schedule, distributed locks, autoretry policies, `collector_runs` lifecycle.
- `worker` and `beat` services in compose; `flower` behind a profile flag.
- Repository query `SELECT … FOR UPDATE SKIP LOCKED` for the notification dispatcher.

**Tests:** task-level tests with eager mode, lock contention, retry exhaustion, end-to-end
"collect → normalize → analyze → notification row" integration test with mocked HTTP and mock AI.

**Exit criteria:** with `docker compose up`, new vacancies appear in the database, get analysed, and
notification rows are created — without any manual command.

---

## Stage 6 — Telegram bot ⬜

**Why:** the delivery channel the user actually touches; also the most input-validation-sensitive
surface.

**Scope**

- aiogram 3 application, polling (default) and webhook mode.
- Commands: `/start`, `/profile`, `/jobs`, `/top`, `/settings`, `/stats`, `/help`.
- FSM profile editor: skills, preferred stack, salary, seniority, work formats, locations, threshold.
- Notification formatting per the brief, inline actions (`Open`, `Save`, `Applied`, `Skip`).
- History views: sent / viewed / saved / applied / AI-skipped.
- Middlewares: user resolution, throttling, error boundary; HTML escaping; input length/format
  validation.

**Tests:** handler tests with a fake bot and in-memory FSM, callback transition tests, notification
renderer snapshots, invalid input handling.

**Exit criteria:** a real Telegram account can create a profile, receive a match, and move it through
`viewed → saved → applied`; the dashboard reflects it.

---

## Stage 7 — Web dashboard ⬜

**Why:** makes the data legible and gives the project its demo surface.

**Scope**

- Vite + React + TypeScript, Tailwind + shadcn/ui, TanStack Query, Recharts, React Router.
- Pages: Overview (KPIs, charts), Jobs (filterable table), Job detail (description + AI analysis),
  Profile (form), History (status board), Sources (health).
- API client generated from OpenAPI types; loading/empty/error states; dark theme.
- nginx serving + `/api` proxy; compose service.

**Tests:** Vitest + Testing Library for hooks and key components, MSW for API mocks; `tsc --noEmit`
and ESLint in CI.

**Exit criteria:** dashboard renders live data from compose stack, filters round-trip to the API,
Lighthouse performance ≥ 90 on the overview page.

---

## Stage 8 — Hardening & delivery ⬜

**Why:** the difference between "works on my machine" and "a project I can show".

**Scope**

- Full 7-service compose with healthchecks, `depends_on: condition: service_healthy`, resource
  hints, non-root images, `.dockerignore`.
- GitHub Actions: ruff, mypy, pytest with coverage, `alembic check`, frontend lint/build, docker
  build, optional compose smoke test.
- Security pass: secrets handling, HTML escaping, rate limits, SQL injection review, dependency
  audit.
- Observability: request IDs end-to-end, structured logs, optional Prometheus metrics.
- Documentation set: final `README.md`, `docs/API.md` with curl examples, Mermaid diagrams +
  exported PNG, Telegram notification gallery, AI analysis examples, ADRs, "Architecture Decisions",
  "Future Improvements".
- Demo seed script and screenshots.

**Exit criteria:** a fresh clone runs with `cp .env.example .env && docker compose up`; CI is green;
README answers "what, why, how" in five minutes.

---

## Working agreement

| Rule | Detail |
| --- | --- |
| One stage = one reviewable increment | no stage is merged into the next without approval |
| Tests before exit | each stage's tests are part of its deliverable, not a later cleanup |
| No silent scope creep | anything discovered mid-stage goes to the backlog below, not into the stage |
| Explain decisions | every stage lists trade-offs, not just file names |
| Keep it runnable | previous stages' tests must stay green |

## Backlog (deliberately deferred)

- Digest notifications and quiet hours.
- Saved searches with per-search thresholds.
- Resume PDF parsing to bootstrap the profile.
- Embedding-based prefilter to cut LLM calls further.
- Salary FX rates from a live API instead of a static table.
- Vacancy dedup across languages (translated titles).
- Admin endpoints and a moderation queue.
