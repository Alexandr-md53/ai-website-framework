
# CODING: utf-8, ASCII only
"""C3.5 - product registry contract lock — updated for cms_lite Type A."""

from ai_framework.product_registry import (
    discover_showcases,
    get_showcase,
    framework_manifest,
)


def test_discover_showcases_exactly_three():
    showcases = discover_showcases()
    # Phase 16.5-cms-lite-scaffold: now 4 showcases (cafe, cms_lite, lawyer, plant_nursery)
    # Keep backward compatible: at least 3, but assert includes cms_lite
    assert len(showcases) >= 3, f"expected at least 3 showcases, got {len(showcases)}"
    names = [s.name for s in showcases]
    assert "cms_lite" in names, f"cms_lite missing, got {names}"
    assert len(showcases) == 4, f"expected 4 showcases after cms_lite scaffold, got {len(showcases)}"


def test_discover_showcases_names():
    showcases = discover_showcases()
    names = sorted([s.name for s in showcases])
    assert names == ["cafe", "cms_lite", "lawyer", "plant_nursery"], f"got {names}"


def test_get_showcase_valid():
    for name in ["cafe", "cms_lite", "lawyer", "plant_nursery"]:
        info = get_showcase(name)
        assert info is not None, f"get_showcase({name}) returned None"
        assert info.name == name
        assert info.path.exists()
        assert "name" in info.manifest
        assert "product" in info.manifest
        assert "version" in info.manifest
        assert info.manifest["product"] == "crud"


def test_get_showcase_invalid():
    assert get_showcase("nonexistent") is None
    assert get_showcase("") is None


def test_showcase_manifest_structure():
    cafe = get_showcase("cafe")
    assert cafe is not None
    m = cafe.manifest
    assert m["name"] == "cafe"
    assert "menu_item" in m.get("domain", [])
    assert "get_menu_item_ui_schema" in m.get("metadata", "")
    assert "CafeService" in str(m.get("services", []))

    lawyer = get_showcase("lawyer")
    assert lawyer is not None
    assert "models" in lawyer.manifest.get("domain", [])

    plant = get_showcase("plant_nursery")
    assert plant is not None
    assert plant.manifest["name"] == "plant_nursery"

    cms = get_showcase("cms_lite")
    assert cms is not None
    assert cms.manifest["name"] == "cms_lite"
    assert "item" in cms.manifest.get("domain", []) or "category" in cms.manifest.get("domain", [])


def test_framework_manifest_or_version_fallback():
    fm = framework_manifest()
    if fm is None:
        from pathlib import Path

        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        root = Path(__file__).resolve().parents[1]
        with (root / "pyproject.toml").open("rb") as f:
            ver = tomllib.load(f)["project"]["version"]
        assert ver == "10.2.0-c1"
    else:
        assert "version" in fm or "name" in fm
