# CODING: utf-8, ASCII only
"""C4.2 - single canonical manifest contract."""

from pathlib import Path
import json
import shutil
import tempfile
from ai_framework.tools.scaffold import scaffold_crud, validate_scaffold


def test_c42_single_manifest():
    tmp = Path(tempfile.mkdtemp())
    try:
        dest = scaffold_crud("my_project", tmp)
        assert (dest / "manifest.json").exists(), "root manifest missing"
        assert not (dest / "showcases" / "my_project" / "manifest.json").exists(), (
            "C4.2: nested manifest must NOT exist"
        )
        errors = validate_scaffold(dest)
        assert errors == [], f"C4.2 contract failed: {errors}"
        data = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
        assert data["product"] == "crud"
        assert data["name"] == "my_project"
        assert data["package"] == "showcases.my_project"
        assert data["domain"]
        assert data["metadata"]
        assert data["services"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_c42_validate_ok():
    tmp = Path(tempfile.mkdtemp())
    try:
        dest = scaffold_crud("test_valid", tmp)
        assert validate_scaffold(dest) == []
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_c42_rejects_duplicate():
    tmp = Path(tempfile.mkdtemp())
    try:
        dest = scaffold_crud("dup_check", tmp)
        (dest / "showcases" / "dup_check" / "manifest.json").write_text(
            "{}", encoding="utf-8"
        )
        errors = validate_scaffold(dest)
        assert any("duplicate" in e.lower() for e in errors), (
            f"should reject duplicate, got {errors}"
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
