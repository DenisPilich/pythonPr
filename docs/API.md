# API reference

Base URL: `http://localhost:8000/api/v1` · interactive docs: `/docs` · schema: `/openapi.json`

The API follows a small, consistent contract:

- **JSON in, JSON out.** Money is a decimal string in the payload (`"5000.00"`), never a float.
- **Errors are `application/problem+json`** with `type`, `title`, `status`, `detail`, `code`,
  `instance` and `request_id`.
- **Pagination** is `limit` / `offset`; every list response is `{items, total, limit, offset}`.
- **Filter values are repeated** to OR them: `?technology=python&technology=docker`.

## Authentication and identity

| Header | Used by | Meaning |
| --- | --- | --- |
| `X-API-Key` | `POST /jobs/{id}/analyze`, `POST/PUT /profile` | Shared operator key (`API_KEY`) |
| `X-Telegram-Id` | profile, history, analyze | Which user the request acts for |

Without `X-Telegram-Id` the configured `DEMO_TELEGRAM_ID` is used, which is what the dashboard does
out of the box. The key check uses a constant-time comparison. This is a portfolio-scale trust
model: for a real multi-tenant deployment, replace the header with per-user sessions/OIDC.

## Health and metadata

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health/live` | Process is up |
| `GET` | `/health/ready` | Database and Redis reachable |
| `GET` | `/meta` | Name, version, environment, API prefix |

```bash
curl http://localhost:8000/health/ready
# {"status":"ok","version":"0.1.0","checks":{"database":"ok","redis":"ok"}}
```

## Jobs

### `GET /jobs`

| Parameter | Type | Notes |
| --- | --- | --- |
| `q` | string ≤ 200 | Full-text over title + description |
| `source` | string | Source code (`hh`, `remoteok`, `remotive`, `arbeitnow`, `weworkremotely`) |
| `company` | string | Company name substring |
| `technology` | repeated slug | `python`, `fastapi`, … |
| `seniority` | repeated enum | `intern`, `junior`, `middle`, `senior`, `lead`, `unknown` |
| `work_format` | repeated enum | `remote`, `hybrid`, `office`, `unknown` |
| `language` | repeated enum | `en`, `ru`, `de`, … |
| `min_salary` / `max_salary` | decimal | Monthly EUR floor/ceiling |
| `published_after` / `published_before` | datetime | ISO-8601 |
| `include_inactive` | bool | Default `false` |
| `sort` | enum | `published_at` (default), `created_at`, `salary`, `title` |
| `order` | enum | `desc` (default), `asc` |
| `limit` / `offset` | int | Default 20, max 100 |

```bash
curl "http://localhost:8000/api/v1/jobs?q=python&technology=fastapi&seniority=senior&limit=5"
```

```json
{
  "items": [
    {
      "id": "5d0f...",
      "title": "Senior Python Developer",
      "company": {"id": "...", "name": "Acme", "normalized_name": "acme"},
      "url": "https://remoteok.com/remote-jobs/...",
      "location_raw": "Worldwide",
      "work_format": "remote",
      "seniority": "senior",
      "language": "en",
      "salary_min": "60000.00",
      "salary_max": "80000.00",
      "salary_currency": "EUR",
      "salary_period": "year",
      "salary_monthly_eur": "5833.33",
      "technologies": [{"slug": "python", "name": "Python", "category": "language"}],
      "sources": [{"source": "remoteok", "name": "RemoteOK", "url": "..."}]
    }
  ],
  "total": 1,
  "limit": 5,
  "offset": 0
}
```

### `GET /jobs/{id}`

Returns the same shape plus `description`, `created_at`, `updated_at`. Unknown id → `404 not_found`.

### `POST /jobs/{id}/analyze`

Requires `X-API-Key`. Returns the cached analysis when the vacancy, profile hash and prompt version
still match; otherwise calls the provider and caches the result. Response headers:

- `X-Analysis-Cached: true|false`
- `X-Analysis-Skipped: prefilter` when a deterministic prefilter rejected the vacancy.

```bash
curl -X POST http://localhost:8000/api/v1/jobs/<id>/analyze \
  -H "X-API-Key: dev-secret-change-me" \
  -H "X-Telegram-Id: 100000001"
```

```json
{
  "match_score": 82,
  "recommendation": "apply",
  "reason": "Strong Python/FastAPI overlap; salary above the floor.",
  "strong_matches": ["Python", "FastAPI", "PostgreSQL"],
  "missing_skills": ["Kubernetes"],
  "red_flags": [],
  "experience_match": "3+ years required, profile has 3 years",
  "provider": "mock",
  "model": "heuristic-v1",
  "is_degraded": false,
  "prompt_version": "v1"
}
```

### `GET /jobs/{id}/analysis`

Returns the latest stored analysis or `404 not_found` if the vacancy has not been analyzed for the
current user.

## Catalogs

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/companies` | Companies with vacancy counts, `q` filter, pagination |
| `GET` | `/technologies` | Technologies with vacancy counts, `category` filter |

## Statistics

### `GET /stats`

Cached in Redis for 60 seconds (fail-open if Redis is down). Includes vacancy totals, remote share,
per-source health, top technologies/companies, seniority/work-format/language distributions,
analysis summary and collector-run health.

## Profile

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/profile` | Resolve by `X-Telegram-Id`; `404` when not created |
| `POST` | `/profile` | Create; requires API key; `409` if it exists |
| `PUT` | `/profile` | Full replacement/upsert; requires API key |

```bash
curl -X PUT http://localhost:8000/api/v1/profile \
  -H "X-API-Key: dev-secret-change-me" \
  -H "X-Telegram-Id: 100000001" \
  -H "Content-Type: application/json" \
  -d '{
    "headline": "Python backend developer",
    "desired_positions": ["Backend Engineer"],
    "target_seniority": ["middle", "senior"],
    "skills": ["Python", "FastAPI", "PostgreSQL"],
    "preferred_stack": ["FastAPI"],
    "excluded_stack": ["PHP"],
    "english_level": "b2",
    "min_salary_amount": 3000,
    "salary_currency": "EUR",
    "preferred_locations": ["Remote"],
    "work_formats": ["remote"],
    "min_match_score": 70,
    "notifications_enabled": true,
    "max_notifications_per_day": 10
  }'
```

Saving recomputes `profile_hash`; analyses cached for the previous hash are not reused.

## History

### `GET /history`

Returns tracked vacancies for `X-Telegram-Id` with status, match score, notification timestamp and
per-status counts. Unknown users get an empty page, not a 404.

| Parameter | Type | Notes |
| --- | --- | --- |
| `status` | enum | `new`, `viewed`, `saved`, `applied`, `rejected` |
| `limit` / `offset` | int | Default 20 |

```json
{
  "items": [
    {
      "job": {"id": "...", "title": "Senior Python Developer", "...": "..."},
      "status": "saved",
      "match_score": 82,
      "notified_at": "2026-11-12T17:58:00Z",
      "created_at": "2026-11-12T17:58:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0,
  "counts": {"new": 0, "viewed": 0, "saved": 1, "applied": 0, "rejected": 0, "total": 1}
}
```

## Errors

```json
{
  "type": "https://errors.ai-job-radar.dev/not_found",
  "title": "Not Found",
  "status": 404,
  "detail": "Vacancy not found",
  "code": "not_found",
  "instance": "/api/v1/jobs/00000000-0000-0000-0000-000000000000",
  "request_id": "..."
}
```

| Status | Code | When |
| --- | --- | --- |
| `400` | `validation_error` | Bad query/body; `errors[]` lists fields |
| `401` | `unauthorized` | Missing/invalid `X-API-Key` |
| `404` | `not_found` | Unknown vacancy/profile/analysis |
| `409` | `conflict` | Profile already exists |
| `422` | `validation_error` | Pydantic validation |
| `429` | `rate_limited` | Telegram/HTTP upstream limits (bot internal) |
| `502` | `ai_provider_error` | LLM failed and no heuristic fallback |
| `503` | `service_unavailable` | Readiness probe failed |
