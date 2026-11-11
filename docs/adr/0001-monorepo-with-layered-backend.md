# ADR-0001: Monorepo with a strictly layered backend

- **Status:** Accepted
- **Date:** 2026-11-11
- **Deciders:** project author

## Context

The product has four runtimes that share one domain: an HTTP API, background workers, a Telegram bot
and a web dashboard. They must be developed and demoed together — a reviewer should clone once and
run once. At the same time the backend must not become a bag of scripts: collectors, LLM calls and
Telegram delivery are exactly the parts that change most often, and they must be replaceable without
touching business rules.

## Decision

1. **One repository**, top-level split by deployable: `backend/`, `frontend/`, `docs/`, `infra/`.
   The only cross-boundary artifact is the OpenAPI schema, consumed by the frontend.
2. **One Python package** `app` with strict layering and a one-way dependency rule:

   ```
   entrypoints (api, bot, tasks) → services → domain / ports
   adapters (collectors, ai, repositories, bot.notifier) → domain / ports
   ```

3. **Ports are `typing.Protocol`s** owned by `app/ports`, not by the adapters. A service imports
   `AIProvider`, never `openai`; a collector imports `httpx`, never a service.
4. Import direction is enforced by review plus `ruff` import rules (`flake8-tidy-imports` banned
   modules per package); mypy `--strict` catches the rest.

## Consequences

**Positive**

- One `docker compose up`, one CI pipeline, one version of the truth.
- The AI provider, collectors and notifier are unit-testable with fakes — no network in tests.
- Adding a job source touches `collectors/` and a seed row only.

**Negative / accepted costs**

- Python packaging must be explicit (`backend/pyproject.toml`, `PYTHONPATH`/install in Docker);
  a flat layout would have been slightly simpler.
- Cross-layer shortcuts are tempting; the ban list and code review are the only enforcement.
- Frontend has no compile-time coupling to the API; drift is caught by an OpenAPI snapshot test.

## Alternatives considered

| Alternative | Why not |
| --- | --- |
| Separate repositories per component | harder to demo, version drift, duplicated CI and Docker setup |
| Single flat `app/` at repository root | frontend node_modules and backend venv pollute one tree |
| Django + DRF | excellent for CRUD, but async collection and explicit ports/adapters are cleaner in FastAPI + SQLAlchemy 2.0 |
| Shared Python package for schemas | the frontend cannot import Python; OpenAPI already is the contract |
