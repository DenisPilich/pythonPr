"""Small operational CLI.

Usage:
    python -m app.cli seed
    python -m app.cli check-db
    python -m app.cli version
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence

from app import __version__
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.seed import seed_reference_data
from app.db.session import Database


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app.cli", description="AI Job Radar operations")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("seed", help="Upsert sources and technologies")
    subparsers.add_parser("check-db", help="Verify database connectivity")
    subparsers.add_parser("version", help="Print the application version")
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
    raise SystemExit(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
