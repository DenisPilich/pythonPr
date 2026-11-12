# ADR 0005 — Idempotent notification outbox behind a `Notifier` port

- **Status:** accepted
- **Date:** 2026-11-12
- **Context:** Stage 5 (Celery automation) and Stage 6 (Telegram delivery)

## Context

Matches are produced by Celery tasks that can retry, run concurrently in several worker processes and
overlap with the next beat tick. Sending a Telegram message directly from the analysis task would
mean:

- duplicate messages whenever a task is retried after a partial failure;
- no way to enforce a daily quota or a minimum score at delivery time;
- vendor code (`aiogram`) leaking into the analysis use case;
- no audit trail of what was sent, when and with which message id.

## Decision

1. **Persist intent before delivery.** Analysis writes a `notifications` row with a unique constraint
   on `(user_id, vacancy_id, channel)`. Enqueue is `INSERT ... ON CONFLICT DO NOTHING`, so retries and
   overlapping tasks cannot create a second notification for the same match.
2. **Claim batches with `FOR UPDATE SKIP LOCKED`.** The dispatcher locks up to `notification_batch_size`
   pending rows, which lets several workers run concurrently without sending the same row twice.
3. **Keep delivery behind the `Notifier` port.** `NotificationService` renders the message and calls
   `send_vacancy(NotificationMessage)`; `LoggingNotifier` is the offline default and
   `TelegramNotifier` the production adapter. Services never import `aiogram`.
4. **Record the outcome.** Success stores `message_id` and `sent_at`; failure stores `last_error` and
   increments `attempts`. Rows are not retried forever: the dispatcher marks exhausted rows failed.
5. **Quota at dispatch, not at enqueue.** `max_notifications_per_day` is checked against
   `notifications` sent today, so a burst of matches cannot exceed the user's limit.
6. **Do not block the analysis path.** A Telegram outage only fails notifications; analyses and
   collection continue, and the next beat tick retries pending rows.

## Consequences

**Positive**

- Exactly one delivery attempt per `(user, vacancy)` is guaranteed by the database, not by task
  bookkeeping.
- The dispatcher can be scaled horizontally and restarted safely.
- Swapping channels (Telegram → email/Slack) means one new adapter, no service changes.
- Every notification is observable and testable without network calls.

**Negative / trade-offs**

- An extra table write and a second task hop add latency (seconds, not minutes) before delivery.
- `SKIP LOCKED` needs PostgreSQL; a different database would require another claim strategy.
- The uniqueness constraint is per channel; adding a second channel intentionally creates a second
  row.
- The quota check is a read-then-write inside one transaction; at extreme concurrency it can slightly
  overshoot unless the dispatcher serialises per user. For this project's volumes that is acceptable
  and documented.

## Alternatives considered

- **Send directly from the analysis task** — simplest, but duplicates on retry and couples the use
  case to aiogram. Rejected.
- **Celery `task_id` as idempotency key** — protects a single task, not the business fact "this user
  was already told about this vacancy". Rejected.
- **Redis queue of pending messages** — fast but loses durability and auditability; PostgreSQL is
  already the source of truth. Rejected.
