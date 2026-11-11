# ADR-0003: Canonical vacancy with source provenance

- **Status:** Accepted
- **Date:** 2026-11-11
- **Deciders:** project author

## Context

The same job is routinely syndicated: a company posts on hh.ru, an aggregator mirrors it to
RemoteOK, a newsletter republishes it. Naively storing one row per fetched item produces duplicate
notifications — the single most annoying failure mode of a job monitor — and skews every statistic
("top technologies" counts the same job three times).

The obvious keys all fail in practice:

- **URL** — differs per board, and tracking parameters (`utm_source`, `?ref=`) defeat it.
- **Title + company** — collapses genuinely distinct openings (two backend roles at one company).
- **Full description hash** — every board rewrites whitespace, boilerplate and benefits; the same job
  hashes differently.

## Decision

1. `vacancies` is the **canonical** posting: one row per real-world job.
2. `vacancy_sources` is **provenance**: one row per `(source_id, external_id)`, linked to the
   canonical vacancy, carrying the source URL and the raw payload.
3. Deduplication is **two-level**:
   - `UNIQUE(source_id, external_id)` — idempotency for collector re-runs;
   - `UNIQUE(vacancies.fingerprint)` where
     `fingerprint = sha256(company_key | title_key | location_key)`.
4. Processing is an **upsert**:
   - fingerprint hit → attach a source reference to the existing vacancy, refresh `last_seen_at`, and
     replace the description only if the new one is richer (longer clean text);
   - fingerprint miss → insert vacancy + first source reference.
5. `content_hash = sha256(description_clean)` decides whether re-analysis is needed. Analysis and
   notification are keyed on `(vacancy, user)`, so a duplicate can never produce a second message:
   `user_vacancies` and `notifications` are unique per pair.
6. `fingerprint_version` allows changing the formula later with a backfill migration instead of a
   silent split/merge of existing data.

## Consequences

**Positive**

- One notification per real job regardless of how many boards carry it.
- Statistics are not inflated by syndication.
- `raw_payload` keeps an audit trail; descriptions can be re-normalized without re-fetching.
- A broken source can be removed without orphaning vacancies.

**Negative / accepted costs**

- Ingest is an upsert with a company get-or-create and technology merge — more code than `INSERT`.
- Two different openings with identical title, company and location merge incorrectly. Rare, and
  detectable because both source URLs remain visible in `vacancy_sources`.
- Salary is excluded from the fingerprint on purpose (one source often omits it), which weakens
  discrimination slightly.
- A fingerprint-version bump requires a maintenance migration.

## Alternatives considered

| Alternative | Why not |
| --- | --- |
| One row per fetched item | duplicate notifications and inflated stats — the exact problem we are solving |
| Unique URL | defeated by tracking parameters and per-board URLs |
| Fuzzy matching (trigram / embeddings) at ingest | nondeterministic, expensive, needs a threshold; better as a later reconciliation job |
| Store duplicates, dedupe at notification time | every query and aggregate then needs dedup logic; the dashboard would lie |
