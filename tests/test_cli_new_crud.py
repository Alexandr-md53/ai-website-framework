# CODING: utf-8, ASCII only
"""C4.1 - ai-framework new --template crud scaffolding."""

from pathlib import Path
import json
import shutil
import tempfile
from ai_framework.tools.scaffold import list_templates, scaffold_crud


def test_c41_list_templates_contains_crud():
    templates = list_templates()
    assert "crud" in templates, f"crud template missing, found: {templates}"


def test_c41_scaffold_crud_creates_structure():
    tmp = Path(tempfile.mkdtemp())
    try:
        dest = scaffold_crud("test_cafe", tmp, "Test cafe")
        assert dest.exists()
        assert (dest / "pyproject.toml").exists()
        assert (dest / "manifest.json").exists() or (
            dest / "showcases" / "test_cafe" / "manifest.json"
        ).exists()

        # check showcase manifest is valid product=crud
        m_path = dest / "showcases" / "test_cafe" / "manifest.json"
        assert m_path.exists(), f"showcase manifest missing at {m_path}"
        data = json.loads(m_path.read_text(encoding="utf-8"))
        assert data["product"] == "crud"
        assert data["version"] == "10.2.0-c1"
        assert data["name"] == "test_cafe"
        assert "domain" in data

        # check subfolders
        for sub in ["domain", "metadata", "services"]:
            assert (dest / "showcases" / "test_cafe" / sub).exists()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_c41_scaffold_invalid_name_raises():
    tmp = Path(tempfile.mkdtemp())
    try:
        try:
            scaffold_crud("123-invalid", tmp)
            assert False, "should raise ValueError for invalid name"
        except ValueError:
            pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_c41_no_core_imports_in_scaffold():
    # B3 - scaffold.py must not import ai_framework core modules
    scaffold_file = (
        Path(__file__).resolve().parents[1] / "ai_framework" / "tools" / "scaffold.py"
    )
    text = scaffold_file.read_text(encoding="utf-8")
    forbidden = [
        "from ai_framework.core",
        "from ai_framework.domain",
        "import showcases",
        "from showcases",
    ]
    for pat in forbidden:
        assert pat not in text, f"B3 violation in scaffold.py: found '{pat}'"


def test_c41_cli_new_list():
    import subprocess, sys

    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "ai_framework.cli.main", "new", "--list"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "crud" in result.stdout
