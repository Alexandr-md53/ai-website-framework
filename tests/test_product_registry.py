# CODING: utf-8, ASCII only
"""C3.5 - product registry contract lock."""

from ai_framework.product_registry import (
    discover_showcases,
    get_showcase,
    framework_manifest,
)


def test_discover_showcases_exactly_three():
    showcases = discover_showcases()
    assert len(showcases) == 3, f"expected 3 showcases, got {len(showcases)}"


def test_discover_showcases_names():
    showcases = discover_showcases()
    names = sorted([s.name for s in showcases])
    assert names == ["cafe", "lawyer", "plant_nursery"]


def test_get_showcase_valid():
    for name in ["cafe", "lawyer", "plant_nursery"]:
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
