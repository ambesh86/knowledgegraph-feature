"""Therapeutic focus areas — loaded, never redefined.

The taxonomy already exists in `ingestion/src/pipeline/config/research_areas.yaml`,
derived from CSL's actual seeded portfolio (`bin/seed/csl_behring_assets.cypher`)
rather than from generic therapeutic categories. This module reads that file.

It does not restate it. There were already three places the taxonomy could have been
typed — the ingestion YAML, `agents/eugene-agent-ui-next/lib/atlas/areas.ts`, and the
digest router (which deliberately takes keywords from its caller for exactly this
reason). A fourth copy, hand-transcribed into a scoring engine, would be the one that
silently drifts and then quietly mis-scores every signal in an entire franchise.

The UI's `FOCUS_AREAS` is a different, coarser taxonomy (hematology / nephrology /
immunology / oncology) used for user profile assignment. `ui_area_map` bridges the two
so a user whose profile says "hematology" sees the hemophilia and bleeding-reversal
areas without either taxonomy having to change.
"""
from __future__ import annotations

import functools
import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

def _repo_checkout_candidate() -> Path | None:
    """Where the ingestion tree sits relative to this file in a dev checkout.

    Guarded because the depth differs between environments: in a checkout this file
    is `<repo>/agents/eugene-scout/src/scout/areas.py` (four levels below the repo
    root), but in the image it is `/app/src/scout/areas.py` — only three. An
    unguarded `parents[4]` raised IndexError at import time and crash-looped the
    container, while every test and local run passed. The container has the YAML
    copied to /app/config anyway, so it never needs this branch.
    """
    here = Path(__file__).resolve()
    if len(here.parents) <= 4:
        return None
    return here.parents[4] / "ingestion/src/pipeline/config/research_areas.yaml"


# In the container the YAML is copied to /app/config; in a dev checkout it is read
# from the ingestion tree directly. Both paths are tried so tests need no fixture
# copy and the image needs no bind mount.
_CANDIDATES = [
    Path(os.environ.get("SCOUT_AREAS_CONFIG", "")) if os.environ.get("SCOUT_AREAS_CONFIG") else None,
    Path("/app/config/research_areas.yaml"),
    _repo_checkout_candidate(),
]


class AreaConfigError(RuntimeError):
    """The taxonomy could not be loaded. Fatal at startup — a scanner with no
    declared areas would scan nothing and report success, which is worse than
    refusing to boot."""


class Area:
    """One therapeutic area and the queries that sweep it."""

    __slots__ = ("id", "label", "enabled", "literature_query", "trials_condition",
                 "trials_intervention", "keywords")

    def __init__(self, raw: dict[str, Any]) -> None:
        self.id: str = str(raw.get("id") or "").strip()
        if not self.id:
            raise AreaConfigError(f"area with no id: {raw!r}")
        self.label: str = str(raw.get("label") or self.id)
        self.enabled: bool = bool(raw.get("enabled", True))
        queries = raw.get("queries") or {}
        # `>-` folded YAML scalars arrive with embedded newlines; the APIs want one line.
        self.literature_query: str = _flatten(queries.get("literature"))
        self.trials_condition: str = _flatten(queries.get("trials_condition"))
        self.trials_intervention: str = _flatten(queries.get("trials_intervention"))
        self.keywords: tuple[str, ...] = tuple(
            str(k).lower().strip() for k in (raw.get("keywords") or []) if str(k).strip()
        )
        if not self.keywords:
            raise AreaConfigError(f"area {self.id!r} declares no keywords; it would match nothing")

    def trials_query(self) -> str:
        """ClinicalTrials.gov v2 `query.term` is a single free-text field, so the
        condition and intervention terms are combined rather than sent separately."""
        parts = [p for p in (self.trials_condition, self.trials_intervention) if p]
        return " OR ".join(f"({p})" for p in parts) if parts else self.label

    def patent_query(self) -> str:
        """A deliberately tighter query than literature.

        The Europe PMC patent corpus is ~1.6k records for `factor VIII` against ~58k
        for the equivalent literature search. A long AND-joined phrase that works
        well against MED returns nothing at all against PAT, so patents get the bare
        keywords OR-ed together instead.
        """
        terms = [k for k in self.keywords if len(k) > 3][:8]
        return " OR ".join(f'"{t}"' for t in terms) if terms else self.label

    def edgar_query(self) -> str:
        """EDGAR full-text search is a phrase search over filing text. Two or three
        distinctive disease/asset terms find material events; the full keyword list
        would be too narrow to match any single filing."""
        terms = [k for k in self.keywords if len(k) > 4][:3]
        return " OR ".join(f'"{t}"' for t in terms) if terms else f'"{self.label}"'

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Area {self.id} enabled={self.enabled} keywords={len(self.keywords)}>"


def _flatten(value: Any) -> str:
    return " ".join(str(value or "").split())


def _config_path() -> Path:
    for candidate in _CANDIDATES:
        if candidate and candidate.is_file():
            return candidate
    tried = [str(c) for c in _CANDIDATES if c]
    raise AreaConfigError(f"research_areas.yaml not found; tried: {tried}")


@functools.lru_cache(maxsize=1)
def load_areas() -> dict[str, Area]:
    """Parse the taxonomy. Cached — the file is immutable for a process lifetime."""
    path = _config_path()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise AreaConfigError(f"{path} is not valid YAML: {e}") from e

    entries = raw.get("areas") or []
    if not entries:
        raise AreaConfigError(f"{path} declares no areas")

    areas = {}
    for entry in entries:
        area = Area(entry)
        areas[area.id] = area
    logger.info(f"loaded {len(areas)} areas from {path} "
                f"({sum(1 for a in areas.values() if a.enabled)} enabled)")
    return areas


def enabled_areas(only: list[str] | None = None) -> list[Area]:
    """Areas to sweep. `only` (from ScanConfig.enabled_areas) narrows further; an
    empty or absent list means every area the YAML has enabled."""
    areas = [a for a in load_areas().values() if a.enabled]
    if only:
        wanted = set(only)
        areas = [a for a in areas if a.id in wanted]
    return sorted(areas, key=lambda a: a.id)


def get_area(area_id: str) -> Area | None:
    return load_areas().get(area_id)


# ---------------------------------------------------------------------------
# Bridging the UI's coarser profile taxonomy
# ---------------------------------------------------------------------------

# Keys are the ids in agents/eugene-agent-ui-next/lib/atlas/areas.ts (which drive the
# `users.focus_area` column); values are ids in research_areas.yaml. A user's Radar is
# the union of the mapped areas. Anything unmapped falls back to every enabled area,
# which is the right failure mode: showing an analyst too much beats showing nothing.
# The UI's focus-area list now mirrors this taxonomy one-for-one
# (`agents/eugene-agent-ui-next/lib/atlas/areas.ts`), so a profile value is normally
# just a scan area id and needs no translation at all.
#
# This map exists only for the ids that predate that alignment and still sit in the
# `users.focus_area` column. `nephrology` and `oncology` are in it because CSL has no
# such franchise: they used to resolve to nothing and fall through to "every area",
# which showed an analyst the entire corpus labelled as their focus — a wrong answer
# delivered confidently. Mapping them to the broadest plasma franchise is narrower and
# honest, and Settings offers the corrected list on next visit.
LEGACY_UI_AREA_MAP: dict[str, list[str]] = {
    "hematology": ["hemophilia", "bleeding_reversal"],
    "immunology": ["immunoglobulin", "hereditary_angioedema", "alpha1_antitrypsin"],
    "nephrology": ["immunoglobulin"],
    "oncology": ["immunoglobulin"],
}

# Retained under the old name so nothing importing it breaks.
UI_AREA_MAP = LEGACY_UI_AREA_MAP


def areas_for_ui_area(ui_area: str | None) -> list[str]:
    """Map a user's profile focus area onto scan area ids.

    Resolution order: the value IS a scan area (the normal case now), then the legacy
    map, then every enabled area. The last branch should be unreachable for any real
    profile value and exists so an unrecognised id shows too much rather than nothing.
    """
    if not ui_area:
        return [a.id for a in enabled_areas()]

    enabled = {a.id for a in enabled_areas()}
    key = ui_area.lower().strip()

    if key in enabled:
        return [key]

    mapped = [a for a in LEGACY_UI_AREA_MAP.get(key, []) if a in enabled]
    return mapped or [a.id for a in enabled_areas()]
