# Architecture Decision Records

Short, immutable records of decisions that are expensive to reverse. Format:
[Michael Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).

| ID | Title | Status |
| --- | --- | --- |
| [0001](0001-monorepo-with-layered-backend.md) | Monorepo with a strictly layered backend | Accepted |
| [0002](0002-celery-redis-over-apscheduler.md) | Celery + Redis instead of APScheduler | Accepted |
| [0003](0003-canonical-vacancy-with-source-provenance.md) | Canonical vacancy with source provenance | Accepted |
| [0004](0004-profile-attributes-as-arrays.md) | Profile attributes as PostgreSQL arrays | Accepted |

New records are added when a decision changes a boundary (module ownership, storage shape, external
contract), not for library choices that are cheap to swap.
