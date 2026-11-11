# ADR-0002: Celery + Redis instead of APScheduler

- **Status:** Accepted
- **Date:** 2026-11-11
- **Deciders:** project author

## Context

The service must poll five sources every 15 minutes, retry failures, fan out per-vacancy LLM analysis,
and send notifications without duplicating them. The brief allows APScheduler if Celery is
overkill. The realistic deployment already has two application processes (API and bot), each of
which would start its own in-process scheduler, and the demo runs several uvicorn workers.

## Decision

Use **Celery 5 with Redis** as broker and result backend, and a **single beat** container for
scheduling. Beat only enqueues; all I/O happens in workers.

Key configuration: `acks_late=True`, `worker_prefetch_multiplier=1`,
`task_reject_on_worker_lost=True`, `visibility_timeout=3600`, `worker_max_tasks_per_child=200`,
UTC everywhere, JSON serializer only.

Async code inside tasks uses `asyncio.run()` per task with a per-worker engine/session factory —
Celery's execution model is synchronous, and pretending otherwise (a persistent loop shared between
tasks) creates cross-task state leaks that are worse than the small per-task setup cost.

## Consequences

**Positive**

- Retries, backoff, visibility timeouts, queues and rate limits are configuration, not code.
- Distributed locks (`SET NX PX`) make overlapping collection runs impossible even with N workers.
- `collector_runs` + `celery_task_id` give a correlation id from a DB row to worker logs.
- The notification dispatcher can use `SELECT … FOR UPDATE SKIP LOCKED` safely with any worker count.

**Negative / accepted costs**

- Two more containers (`worker`, `beat`) to operate and document.
- No native async; each task pays loop setup and engine creation. Acceptable at this scale, and
  measured in the task tests.
- Tests need `task_always_eager` and a broker-less configuration; a small fixture handles it.

## Alternatives considered

| Alternative | Why not |
| --- | --- |
| APScheduler inside the API | with >1 uvicorn worker the schedule runs N times; no retries, no visibility, no distributed coordination |
| `arq` | elegant and async-native, smaller ecosystem, weaker scheduling/monitoring story for a portfolio piece |
| Cron + `manage.py`-style commands | no retries, no backoff, no observability without extra plumbing |
| Celery with RabbitMQ | Redis is already required for caching and locks; a second broker adds ops cost for no benefit here |
