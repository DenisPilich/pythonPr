# ADR-0004: Profile attributes as PostgreSQL arrays

- **Status:** Accepted
- **Date:** 2026-11-11
- **Deciders:** project author

## Context

A `UserProfile` is a small, user-owned document: a handful of skill names, preferred stack, target
seniority levels, work formats, locations, salary floor and a notification threshold. It is always
read and written as a whole, and its content participates in the AI cache key via `profile_hash`.

Two forces pull in opposite directions:

- **Write ergonomics and cache correctness** want one row that can be hashed atomically.
- **Analytics** ("which skills are most requested by users") want normalized tables.

## Decision

Store profile lists as native PostgreSQL arrays (`text[]`, `seniority_level[]`, `work_format[]`) on
`user_profiles`, and compute `profile_hash = sha256(canonical JSON of profile fields)` on every
write. Vacancy-side skills stay normalized in `technologies` / `vacancy_technologies`, because those
are aggregated and filtered.

## Consequences

**Positive**

- One `UPDATE`, no child-row churn, no partial profile states.
- `profile_hash` is a single deterministic value — the AI cache key and the "was this verdict produced
  for the current profile?" check are trivial.
- Fewer tables and joins for the most frequent read (bot `/profile`, analysis input).

**Negative / accepted costs**

- No per-skill proficiency levels and no cheap "users who know X" queries. Adding either requires a
  `user_skills` table and a backfill; the schema is designed so that can be additive.
- Array validation lives in Pydantic, not in the database (no FK to `technologies`). Acceptable: the
  profile is a preference document, not a catalog, and normalization maps free text to canonical
  names on write.
- `profile_hash` must be recomputed in exactly one place; the service layer owns it, and a test
  asserts that editing any tracked field changes the hash.

## Alternatives considered

| Alternative | Why not |
| --- | --- |
| `user_skills`, `user_stack`, … join tables | correct for analytics, but 4 extra tables, joins on every profile read, and multi-statement updates |
| JSONB blob | weaker typing and constraints than arrays; no benefit here |
| Arrays + generated `profile_hash` column | PostgreSQL can hash but not canonicalize JSON ordering; hashing in the service is explicit and testable |
