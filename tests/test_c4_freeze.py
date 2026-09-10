from pathlib import Path
from ai_framework.tools.scaffold import (
    validate_scaffold,
    inspect_project,
    _framework_version,
    scaffold_crud,
)
import tempfile
import shutil

ROOT = Path(__file__).resolve().parents[1]
SHOWCASES = ["cafe", "lawyer", "plant_nursery"]


def _fresh():
    tmp = Path(tempfile.mkdtemp())
    p = scaffold_crud("_c4_probe", tmp, description="probe")
    return p, tmp


def test_all_showcases_single_canonical_manifest():
    for name in SHOWCASES:
        proj = ROOT / "showcases" / name
        assert (proj / "manifest.json").exists(), f"{name} root manifest missing"
        assert not (proj / "showcases" / name / "manifest.json").exists(), (
            f"{name} nested manifest must not exist"
        )

    proj, tmp = _fresh()
    try:
        assert (proj / "manifest.json").exists()
        assert not (proj / "showcases" / proj.name / "manifest.json").exists()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_all_showcases_version_lock_crud_suffix():
    fv = _framework_version()
    for name in SHOWCASES:
        proj = ROOT / "showcases" / name
        # pyproject name must be <name>-crud
        text = (proj / "pyproject.toml").read_text(encoding="utf-8")
        assert f'name = "{name}-crud"' in text, (
            f"{name} pyproject name must be {name}-crud"
        )
        assert f'version = "{fv}"' in text
    proj, tmp = _fresh()
    try:
        text = (proj / "pyproject.toml").read_text(encoding="utf-8")
        assert f'version = "{fv}"' in text
        assert f'name = "{proj.name}-crud"' in text
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_all_showcases_validate_scaffold_pass():
    for name in SHOWCASES:
        proj = ROOT / "showcases" / name
        errs = validate_scaffold(proj)
        assert errs == [], f"{name} validate_scaffold failed: {errs}"
    proj, tmp = _fresh()
    try:
        assert validate_scaffold(proj) == []
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_all_showcases_inspect_filesystem_only_pass():
    for name in SHOWCASES:
        proj = ROOT / "showcases" / name
        info = inspect_project(proj)
        assert info["valid"], f"{name} inspect failed: {info['errors']}"
        assert info["manifest_version"] == _framework_version()
    proj, tmp = _fresh()
    try:
        info = inspect_project(proj)
        assert info["valid"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
