"""Source registry: the only place that knows which collectors exist.

Adding a source means adding a class with a `code` and one entry here; the seeding
step, the API and the task layer read the registry instead of hard-coding names.
"""

from __future__ import annotations

from app.collectors.base import BaseCollector
from app.collectors.http import HttpClient
from app.collectors.sources.arbeitnow import ArbeitnowCollector
from app.collectors.sources.hh import HhCollector
from app.collectors.sources.remoteok import RemoteOkCollector
from app.collectors.sources.remotive import RemotiveCollector
from app.collectors.sources.rss import WeWorkRemotelyCollector
from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.ports.vacancy_source import SourceConfig


COLLECTORS: dict[str, type[BaseCollector]] = {
    collector.code: collector
    for collector in (
        HhCollector,
        RemoteOkCollector,
        RemotiveCollector,
        ArbeitnowCollector,
        WeWorkRemotelyCollector,
    )
}


def build_collector(source: SourceConfig, http: HttpClient, settings: Settings) -> BaseCollector:
    collector_cls = COLLECTORS.get(source.code)
    if collector_cls is None:
        raise ConfigurationError(f"unknown collector: {source.code!r}")
    return collector_cls(http=http, settings=settings, source=source)


def available_codes() -> tuple[str, ...]:
    return tuple(sorted(COLLECTORS))
