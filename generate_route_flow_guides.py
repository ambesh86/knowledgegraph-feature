"""Generate per-route end-to-end PDF flow guides for every Eugene route.

Each section module lives in docs/flow_guide_sections/<route>.py and exports:
    OUT_NAME : str  -- output filename under docs/ (e.g. EUGENE_N_HOP_FLOW_GUIDE.pdf)
    TITLE    : str  -- doc title
    build_story() -> list  -- list of ReportLab flowables

Run: /usr/local/opt/python@3.11/bin/python3.11 generate_route_flow_guides.py
"""
from __future__ import annotations

import importlib
import os
import pkgutil

from docs.flow_guide_sections import _helpers as h


def _iter_section_modules():
    pkg_path = os.path.join(os.path.dirname(__file__), "docs", "flow_guide_sections")
    for info in pkgutil.iter_modules([pkg_path]):
        name = info.name
        if name.startswith("_"):
            continue
        yield importlib.import_module(f"docs.flow_guide_sections.{name}")


def main():
    os.makedirs(h.DOCS_DIR, exist_ok=True)
    for mod in _iter_section_modules():
        h.render(mod.build_story(), mod.OUT_NAME, mod.TITLE)


if __name__ == "__main__":
    main()
