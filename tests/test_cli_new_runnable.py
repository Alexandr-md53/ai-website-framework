# CODING: utf-8, ASCII only
"""C4.3 - generated artifact is runnable/inspectable."""

import sys
import shutil
import tempfile
from pathlib import Path

from ai_framework.tools.scaffold import (
    scaffold_crud,
    inspect_project,
    validate_scaffold,
    _framework_version,
)


def test_c43_canonical_and_structure():
    tmp = Path(tempfile.mkdtemp())
    try:
        dest = scaffold_crud("my_crud", tmp)
        info = inspect_project(dest)
        assert info["valid"], f"C4.3 inspect failed: {info['errors']}"
        assert info["manifest"]["product"] == "crud"
        assert info["manifest"]["package"] == "showcases.my_crud"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_c43_filesystem_only_inspect():
    """inspect_project must not import showcases.<name>"""
    tmp = Path(tempfile.mkdtemp())
    try:
        dest = scaffold_crud("fs_only", tmp)
        # ensure showcases.fs_only NOT in sys.modules before
        assert "showcases.fs_only" not in sys.modules
        info = inspect_project(dest)
        assert info["valid"]
        # after inspect, still NOT imported (filesystem-only)
        assert "showcases.fs_only" not in sys.modules, (
            "inspect_project must be filesystem-only, no import"
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        sys.modules.pop("showcases.fs_only", None)
        sys.modules.pop("showcases.fs_only.domain", None)
        sys.modules.pop("showcases.fs_only.metadata", None)
        sys.modules.pop("showcases.fs_only.services", None)
        sys.modules.pop("showcases", None)


def test_c43_importable_package():
    tmp = Path(tempfile.mkdtemp())
    try:
        dest = scaffold_crud("importable_pkg", tmp)
        for mod in list(sys.modules.keys()):
            if mod == "showcases" or mod.startswith("showcases.importable_pkg"):
                del sys.modules[mod]
        sys.path.insert(0, str(dest))
        try:
            import importlib

            if "showcases" in sys.modules:
                del sys.modules["showcases"]
            importlib.import_module("showcases")
            importlib.import_module("showcases.importable_pkg")
            importlib.import_module("showcases.importable_pkg.domain")
            importlib.import_module("showcases.importable_pkg.metadata")
            importlib.import_module("showcases.importable_pkg.services")
        finally:
            sys.path.remove(str(dest))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        for mod in list(sys.modules.keys()):
            if mod.startswith("showcases.importable_pkg") or mod == "showcases":
                sys.modules.pop(mod, None)


def test_c43_version_lock():
    tmp = Path(tempfile.mkdtemp())
    try:
        dest = scaffold_crud("ver_lock", tmp)
        info = inspect_project(dest)
        assert info["valid"]
        fw = _framework_version()
        assert info["manifest_version"] == fw, (
            f"manifest version {info['manifest_version']}!= {fw}"
        )
        assert info["pyproject_version"] == fw, (
            f"pyproject version {info['pyproject_version']}!= {fw}"
        )
        assert validate_scaffold(dest) == []
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
