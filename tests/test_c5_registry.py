import sys
from ai_framework.tools.scaffold import FRAMEWORK_VERSION


def test_lists_legacy():
    from ai_framework.api.registry import list_products

    products = list_products()
    names = {p.name for p in products}
    assert {"cafe", "lawyer", "plant_nursery"}.issubset(names)
    assert (
        len([p for p in products if p.name in {"cafe", "lawyer", "plant_nursery"}]) == 3
    )


def test_version_lock():
    from ai_framework.api.registry import list_products

    for p in list_products():
        if p.name in {"cafe", "lawyer", "plant_nursery"}:
            assert p.version == FRAMEWORK_VERSION
            assert p.product == "crud"
            assert p.package == f"showcases.{p.name}"
            assert p.path.exists()


def test_no_import_side_effect():
    # import registry must not import showcases.*
    mods_before = set(sys.modules.keys())
    from ai_framework.api import registry as reg_mod
    import importlib

    importlib.reload(reg_mod)
    mods_after = set(sys.modules.keys())
    new_showcases = [m for m in mods_after - mods_before if m.startswith("showcases.")]
    assert new_showcases == [], f"side effect imports: {new_showcases}"
    # filesystem-only: module file should not create files
    from pathlib import Path

    root = Path(reg_mod.__file__).resolve().parents[2] / "showcases"
    assert root.exists()
