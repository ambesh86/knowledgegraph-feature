"""Collector registry.

The orchestrator asks this module what to run rather than importing the four classes
itself, so adding a fifth source is a one-line edit here plus a new file — the
pipeline never learns how many sources exist.
"""
from __future__ import annotations

from scout.collectors.base import BaseCollector, Collector, FetchError, freshest, within_window
from scout.collectors.edgar import EdgarCollector
from scout.collectors.epo import EpoCollector
from scout.collectors.literature import LiteratureCollector
from scout.collectors.patents import PatentsCollector
from scout.collectors.trials import TrialsCollector
from scout.models import SourceId

REGISTRY: dict[SourceId, type[BaseCollector]] = {
    SourceId.TRIALS: TrialsCollector,
    SourceId.LITERATURE: LiteratureCollector,
    SourceId.PATENTS: PatentsCollector,
    SourceId.EDGAR: EdgarCollector,
    SourceId.EPO: EpoCollector,
}


def build(source: SourceId) -> BaseCollector:
    try:
        return REGISTRY[source]()
    except KeyError:
        raise ValueError(f"no collector registered for {source!r}") from None


def all_sources() -> list[SourceId]:
    return list(REGISTRY)


__all__ = [
    "BaseCollector",
    "Collector",
    "EdgarCollector",
    "EpoCollector",
    "FetchError",
    "LiteratureCollector",
    "PatentsCollector",
    "REGISTRY",
    "TrialsCollector",
    "all_sources",
    "build",
    "freshest",
    "within_window",
]
