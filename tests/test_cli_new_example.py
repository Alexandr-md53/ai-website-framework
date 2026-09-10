from pathlib import Path
import json
import shutil
import tempfile
import sys
from ai_framework.tools.scaffold import scaffold_crud, inspect_project


def test_c44_with_example_false_no_examples():
    tmp = Path(tempfile.mkdtemp())
    try:
        dest = scaffold_crud("no_ex_pkg", tmp, with_example=False)
        assert not (dest / "showcases" / "no_ex_pkg" / "domain" / "example.py").exists()
        data = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
        assert "examples" not in data
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_c44_with_example_true_creates_files():
    tmp = Path(tempfile.mkdtemp())
    try:
        dest = scaffold_crud("with_ex_pkg", tmp, with_example=True)
        assert (dest / "showcases" / "with_ex_pkg" / "domain" / "example.py").exists()
        assert (
            dest / "showcases" / "with_ex_pkg" / "metadata" / "example.json"
        ).exists()
        assert (
            dest / "showcases" / "with_ex_pkg" / "services" / "example_service.py"
        ).exists()
        data = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
        assert data["examples"] == ["example"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_c44_with_example_true_importable():
    tmp = Path(tempfile.mkdtemp())
    try:
        dest = scaffold_crud("import_ex_pkg", tmp, with_example=True)
        for m in list(sys.modules.keys()):
            if m.startswith("showcases.import_ex_pkg"):
                del sys.modules[m]
        if "showcases" in sys.modules:
            del sys.modules["showcases"]
        sys.path.insert(0, str(dest))
        try:
            import importlib

            importlib.import_module("showcases.import_ex_pkg.domain.example")
            importlib.import_module("showcases.import_ex_pkg.services.example_service")
        finally:
            sys.path.remove(str(dest))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        for m in list(sys.modules.keys()):
            if m.startswith("showcases.import_ex_pkg") or m == "showcases":
                sys.modules.pop(m, None)


def test_c44_inspect_project_sees_examples():
    tmp = Path(tempfile.mkdtemp())
    try:
        dest = scaffold_crud("inspect_ex_pkg", tmp, with_example=True)
        rep = inspect_project(dest)
        assert rep["valid"] is True
        assert rep["manifest"]["examples"] == ["example"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
