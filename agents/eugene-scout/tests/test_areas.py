"""Taxonomy loading.

The first test here is a regression for a bug that only ever appeared in the
container: `areas.py` computed its dev-checkout fallback path with `parents[4]`,
which exists at `<repo>/agents/eugene-scout/src/scout/areas.py` but not at
`/app/src/scout/areas.py`. It raised `IndexError` during module import, crash-looping
the service, while every unit test and every local run passed — because both run from
a checkout deep enough for the index to resolve.

Anything computed from `__file__` depth is environment-dependent by construction and
needs a test that does not share the environment it was written in.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

from scout.areas import AreaConfigError, areas_for_ui_area, enabled_areas, get_area, load_areas


class TestPathResolution:
    def test_module_imports_from_a_shallow_path(self, tmp_path, monkeypatch):
        """REGRESSION: import must not depend on how deeply the file is nested.

        Reproduces the container layout — a shallow directory with no repo above it —
        and asserts the module still imports.
        """
        shallow = tmp_path / "app" / "src" / "scout"
        shallow.mkdir(parents=True)
        source = Path(load_areas.__module__ and __file__).parent.parent / "src" / "scout" / "areas.py"
        shallow.joinpath("areas.py").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        shallow.joinpath("__init__.py").write_text("", encoding="utf-8")

        monkeypatch.syspath_prepend(str(tmp_path / "app" / "src"))
        monkeypatch.delitem(sys.modules, "scout.areas", raising=False)
        monkeypatch.delitem(sys.modules, "scout", raising=False)

        # Importing must not raise, even though there is no repo four levels up.
        module = importlib.import_module("scout.areas")
        assert module is not None

    def test_explicit_config_path_wins(self, tmp_path, monkeypatch):
        """Patches the candidate list rather than reloading the module.

        `importlib.reload` rebinds every class the module defines, so a test that
        reloads and a test that imported `AreaConfigError` at collection time end up
        comparing two different class objects — `pytest.raises` then fails to catch
        an exception that was, in every meaningful sense, the right one.
        """
        config = tmp_path / "areas.yaml"
        config.write_text(
            "areas:\n"
            "  - id: test_area\n"
            "    label: Test Area\n"
            "    enabled: true\n"
            "    keywords: [alpha, beta]\n",
            encoding="utf-8",
        )
        import scout.areas as areas_module

        monkeypatch.setattr(areas_module, "_CANDIDATES", [config])
        areas_module.load_areas.cache_clear()
        try:
            areas = areas_module.load_areas()
            assert "test_area" in areas
            assert areas["test_area"].keywords == ("alpha", "beta")
        finally:
            areas_module.load_areas.cache_clear()

    def test_missing_config_is_a_clear_error(self, tmp_path, monkeypatch):
        """A scanner with no declared areas would scan nothing and report success,
        which is worse than refusing to boot."""
        import scout.areas as areas_module

        monkeypatch.setattr(areas_module, "_CANDIDATES", [tmp_path / "nope.yaml"])
        areas_module.load_areas.cache_clear()
        try:
            with pytest.raises(areas_module.AreaConfigError, match="not found"):
                areas_module.load_areas()
        finally:
            areas_module.load_areas.cache_clear()


class TestTaxonomy:
    def test_loads_the_real_csl_taxonomy(self):
        areas = load_areas()
        assert "hemophilia" in areas
        assert areas["hemophilia"].keywords

    def test_disabled_areas_are_excluded(self):
        enabled = {a.id for a in enabled_areas()}
        assert all(load_areas()[a].enabled for a in enabled)

    def test_area_without_keywords_is_rejected(self):
        """An area matching nothing would scan and silently return zero, which looks
        identical to a quiet night."""
        from scout.areas import Area

        with pytest.raises(AreaConfigError, match="no keywords"):
            Area({"id": "x", "label": "X", "keywords": []})

    def test_area_without_id_is_rejected(self):
        from scout.areas import Area

        with pytest.raises(AreaConfigError, match="no id"):
            Area({"label": "X", "keywords": ["a"]})

    def test_folded_yaml_queries_are_flattened_to_one_line(self):
        """`>-` scalars arrive with embedded newlines; the APIs want a single line."""
        for area in enabled_areas():
            assert "\n" not in area.literature_query
            assert "\n" not in area.trials_query()

    def test_patent_query_is_looser_than_literature(self):
        """The patent corpus is orders of magnitude smaller; a long AND-joined
        clinical phrase matches nothing against it."""
        area = get_area("hemophilia")
        assert area is not None
        assert " OR " in area.patent_query()


class TestUiAreaBridge:
    def test_a_scan_area_id_resolves_to_itself(self):
        """The normal case now that the UI list mirrors this taxonomy — no
        translation, so a user's choice is honoured exactly."""
        assert areas_for_ui_area("hemophilia") == ["hemophilia"]
        assert areas_for_ui_area("hereditary_angioedema") == ["hereditary_angioedema"]

    def test_resolution_is_case_and_whitespace_tolerant(self):
        assert areas_for_ui_area("  Hemophilia  ") == ["hemophilia"]

    def test_legacy_hematology_still_resolves(self):
        """Existing users.focus_area values must keep working across the rename."""
        assert "hemophilia" in areas_for_ui_area("hematology")

    def test_legacy_unmatched_areas_narrow_rather_than_showing_everything(self):
        """REGRESSION: `nephrology` used to fall through to every enabled area, so an
        analyst saw the whole corpus labelled as their focus — a wrong answer
        delivered confidently. CSL has no nephrology franchise; the honest resolution
        is the nearest real one, not all of them."""
        resolved = areas_for_ui_area("nephrology")
        assert resolved == ["immunoglobulin"]
        assert set(resolved) != {a.id for a in enabled_areas()}

    def test_unknown_area_still_shows_too_much_rather_than_nothing(self):
        assert set(areas_for_ui_area("not-a-real-area")) == {a.id for a in enabled_areas()}

    def test_missing_profile_falls_back_to_everything(self):
        assert set(areas_for_ui_area(None)) == {a.id for a in enabled_areas()}
