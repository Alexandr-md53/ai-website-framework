# CODING: utf-8, ASCII only
"""C3.5 - CLI product/showcase contracts."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_cli(*args):
    cmd = [sys.executable, "-m", "ai_framework.cli.main"] + list(args)
    r = subprocess.run(
        cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8"
    )
    return r.returncode, r.stdout + r.stderr


def test_product_list_contains_three():
    rc, out = _run_cli("product", "list")
    assert rc == 0, out
    assert "cafe" in out
    assert "lawyer" in out
    assert "plant_nursery" in out


def test_showcase_list_contains_names():
    rc, out = _run_cli("showcase", "list")
    assert rc == 0, out
    assert "cafe" in out
    assert "lawyer" in out
    assert "plant_nursery" in out
    assert "found 3" in out or "3" in out


def test_showcase_info_real_manifest():
    for name in ["cafe", "lawyer", "plant_nursery"]:
        rc, out = _run_cli("showcase", "info", name)
        assert rc == 0, out
        assert name in out
        assert "manifest.json" in out
        assert "product" in out
        assert "crud" in out


def test_showcase_info_invalid():
    rc, out = _run_cli("showcase", "info", "nonexistent")
    assert rc != 0
    assert "not found" in out.lower()


def test_b3_guard_no_showcase_imports():
    # C3.3 B3: ai_framework/ must never import showcases as Python module
    # Only real import statements count, not help text or string paths
    import re

    pattern_from = re.compile(r"^\s*from\s+showcases(\.| import)")
    pattern_import = re.compile(r"^\s*import\s+showcases(\b|\.)")
    import_root = ROOT / "ai_framework"
    violations = []
    for py in import_root.rglob("*.py"):
        if py.name == "__pycache__":
            continue
        text = py.read_text(encoding="utf-8", errors="ignore")
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            # Skip string literals that are dotted paths (allowed)
            if pattern_from.search(line) or pattern_import.search(line):
                violations.append(f"{py}:{i}:{line.strip()}")
    assert not violations, f"B3 violations: {violations}"
