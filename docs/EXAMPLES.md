# What the radar produces

Real output from a local run with `AI_PROVIDER=mock` (no paid key): RemoteOK collection, one demo
profile, 50 analysed vacancies, 7 notifications above the 70% threshold.

## 1. Collection

```
$ docker compose exec api python -m app.cli collect remoteok --max-pages 1

{"source": "remoteok", "status": "success", "fetched": 98, "created": 98,
 "updated": 0, "duplicates": 0, "skipped": 0, "duration_ms": 5791,
 "event": "source_collected"}
remoteok         success  fetched=98   created=98   updated=0   duplicates=0   skipped=0   5791ms
```

A second run produces `created=0 duplicates=98`: source-level idempotency is enforced by
`(source_id, external_id)`, while cross-source duplicates collapse into one canonical vacancy with
multiple `vacancy_sources` rows.

## 2. AI verdict

`GET /api/v1/jobs/{id}/analysis` for a real vacancy:

```json
{
  "match_score": 76,
  "recommendation": "apply",
  "reason": "2 of 4 required technologies match (50%). Missing: Git, SQL. Strong fit — worth applying.",
  "experience_match": "Vacancy is middle; target seniority is middle, senior.",
  "skills_match": "2 of 4 required technologies match (50%).",
  "strong_matches": ["Docker", "Python"],
  "missing_skills": ["Git", "SQL"],
  "red_flags": [],
  "provider": "mock",
  "model": "heuristic-v1",
  "is_degraded": false,
  "prompt_version": "v1"
}
```

With `AI_PROVIDER=openai` the same shape comes from the model, validated against the JSON schema in
`app/ai/schema.py`. `is_degraded=true` means the deterministic fallback answered because the provider
failed — the pipeline never loses a vacancy to an LLM outage.

## 3. Telegram message

Rendered by `app/services/notification_format.py`, delivered by `TelegramNotifier` with an inline
keyboard:

```html
🔥 <b>Operations Expert with Python for AI Supply Chain Task Design</b> — Middle

Company: Toptal
Location: Remote
Salary: Not specified

🎯 Match: <b>76%</b>

✅ Хорошее совпадение:
- Docker
- Python

❌ Не хватает:
- Git
- SQL

🤖 AI recommendation:
<b>APPLY</b>

<a href="https://remoteok.com/...">Открыть вакансию</a>
```

Buttons: **🔗 Открыть вакансию** (URL), **💾 Сохранить**, **✅ Applied**, **🚫 Skip**. Each callback
is validated (`vac:<action>:<uuid>`) and moves the tracked row through an explicit state machine:

```
new ──save──> saved ──applied──> applied
 │               │
 └──applied──────┘
 └──skip──> rejected (not allowed after applied)
```

## 4. Bot flow

```
/start      → menu: profile · jobs · top · stats · settings
/profile    → fields + buttons: skills · stack · salary · level · format · threshold
/jobs       → last 5 tracked vacancies with actions
/top        → best matches by score
/stats      → global radar stats + personal history
/settings   → notifications on/off, threshold 50/70/80
```

Editing skills:
you send `Python, FastAPI, PostgreSQL` → the bot parses the list, upserts the profile, recomputes
`profile_hash` and shows the updated card. Old analyses stay cached but are not reused for the new
hash.

## 5. Celery pipeline

```
beat every 15 min → collect_all_sources
                  → collect_source (per-source Redis lock)
                  → normalize + upsert + dedupe
beat every 5 min  → analyze_new_vacancies
                  → analyze_vacancy (prefilter → cache → provider)
beat every 2 min  → send_pending_notifications
                  → claim 20 rows FOR UPDATE SKIP LOCKED → Telegram
                  → mark sent / failed, enforce daily quota
```

Observed locally: `98 vacancies → 50 analyses (avg 41.6) → 7 notifications`, worker connected to
Redis, API healthy, dashboard showing the same data.

## 6. Dashboard

- **Overview** — KPI cards, top technologies bar chart, work-format donut, source health, latest
  arrivals.
- **Jobs** — full-text search + technology/seniority/format/salary filters, sort, pagination.
- **Job detail** — cleaned description, technology chips, source provenance and the AI verdict with
  a **Re-run analysis** button.
- **Profile** — the same profile the bot edits; saving recomputes the hash.
- **History** — per-status counts and the tracked vacancy list.
