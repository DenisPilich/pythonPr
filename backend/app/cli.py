"""Small operational CLI.

Usage:
    python -m app.cli seed
    python -m app.cli check-db
    python -m app.cli collect hh --max-pages 2
    python -m app.cli collect all
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence

from app import __version__
from app.collectors.errors import CollectorError
from app.collectors.http import HttpClient
from app.collectors.registry import build_collector
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.seed import seed_reference_data
from app.db.session import Database
from app.models import Source
from app.normalization.pipeline import NormalizationPipeline
from app.ports.vacancy_source import SourceConfig
from app.repositories.sources import SourceRepository
from app.services.collection import CollectionService


async def _seed() -> int:
    settings = get_settings()
    database = Database(settings)
    logger = get_logger("cli.seed")
    try:
        async with database.session() as session:
            report = await seed_reference_data(session)
    finally:
        await database.dispose()

    logger.info(
        "reference_data_seeded",
        sources=report.sources,
        technologies=report.technologies,
    )
    print(f"seeded: sources={report.sources} technologies={report.technologies}")
    return 0


async def _check_db() -> int:
    database = Database(get_settings())
    try:
        await database.ping()
    finally:
        await database.dispose()
    print("database: ok")
    return 0


def _source_config(source: Source) -> SourceConfig:
    return SourceConfig(
        code=source.code,
        base_url=source.base_url,
        rate_limit_per_min=source.rate_limit_per_min,
        config=source.config,
    )


async def _collect(source_code: str, max_pages: int) -> int:
    settings = get_settings()
    database = Database(settings)
    http = HttpClient(settings)
    pipeline = NormalizationPipeline()
    service = CollectionService(database, pipeline)
    failures = 0

    try:
        async with database.session() as session:
            repository = SourceRepository(session)
            if source_code == "all":
                rows = await repository.list_enabled()
                if not rows:
                    print("no enabled sources; run `python -m app.cli seed` first")
                    return 1
                selected = [(row.id, _source_config(row)) for row in rows]
            else:
                row = await repository.get_by_code(source_code)
                if row is None:
                    print(f"unknown source: {source_code!r}")
                    return 1
                selected = [(row.id, _source_config(row))]

        for source_id, config in selected:
            collector = build_collector(config, http, settings)
            try:
                report = await service.run(config, source_id, collector, max_pages=max_pages)
            except CollectorError as exc:
                failures += 1
                print(f"{config.code:<16} FAILED   {type(exc).__name__}: {exc}")
            else:
                print(
                    f"{report.source_code:<16} {report.status.value:<8} "
                    f"fetched={report.fetched:<4} created={report.created:<4} "
                    f"updated={report.updated:<4} duplicates={report.duplicates:<4} "
                    f"skipped={report.skipped:<3} {report.duration_ms}ms"
                )
    finally:
        await http.aclose()
        await database.dispose()

    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app.cli", description="AI Job Radar operations")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("seed", help="Upsert sources and technologies")
    subparsers.add_parser("check-db", help="Verify database connectivity")
    subparsers.add_parser("version", help="Print the application version")

    collect_parser = subparsers.add_parser("collect", help="Collect vacancies")
    collect_parser.add_argument(
        "source", nargs="?", default="all", help="source code (hh, remoteok, …) or 'all'"
    )
    collect_parser.add_argument("--max-pages", type=int, default=5, help="page limit per source")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "version":
        print(__version__)
        return 0

    configure_logging(get_settings())
    if args.command == "seed":
        return asyncio.run(_seed())
    if args.command == "check-db":
        return asyncio.run(_check_db())
    if args.command == "collect":
        return asyncio.run(_collect(args.source, args.max_pages))
    raise SystemExit(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
