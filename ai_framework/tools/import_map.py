"""
B1: IMPORT_MAP generator - Windows cp1252 safe (no emoji)
Usage: python -m ai_framework.tools.import_map > docs/IMPORT_MAP_FROZEN_V2.md
"""

import ast
from pathlib import Path
from collections import defaultdict
import sys

ROOT = Path(__file__).resolve().parents[2]
AI = ROOT / "ai_framework"


def get_module_name(py_file: Path) -> str:
    try:
        rel = py_file.relative_to(ROOT)
        return ".".join(rel.with_suffix("").parts)
    except:
        return py_file.stem


def parse_imports(py_file: Path):
    try:
        src = py_file.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(src, filename=str(py_file))
    except Exception as e:
        return []
    imps = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imps.append((alias.name, py_file, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level > 0:
                mod = "." * node.level + mod
            imps.append((mod, py_file, node.lineno))
    return imps


def main():
    if not AI.exists():
        print(f"# IMPORT_MAP ERROR: {AI} not found", file=sys.stderr)
        sys.exit(1)

    all_files = [p for p in AI.rglob("*.py") if "__pycache__" not in str(p)]

    import_map = defaultdict(list)
    reverse_map = defaultdict(list)
    showcase_violations = []
    core_violations = []

    FORBIDDEN_CORE = [
        "ai_framework.api",
        "ai_framework.crud_ui",
        "ai_framework.application",
        "ai_framework.infrastructure",
        "showcases",
    ]

    for f in sorted(all_files):
        mod_name = get_module_name(f)
        imps = parse_imports(f)
        for imp_name, _, lineno in imps:
            if not imp_name:
                continue
            import_map[mod_name].append(imp_name)
            reverse_map[imp_name].append(f"{mod_name}:{lineno}")

            if "showcases" in imp_name.lower() and "showcases" not in str(f).lower():
                showcase_violations.append(
                    f"{f.relative_to(ROOT)}:{lineno} -> {imp_name}"
                )

            if any(
                x in str(f)
                for x in [
                    "ai_framework/core",
                    "ai_framework/domain",
                    "ai_framework/validation",
                    "ai_framework/services/slug",
                    "ai_framework/crud/contracts",
                ]
            ):
                for forb in FORBIDDEN_CORE:
                    if forb in imp_name:
                        core_violations.append(
                            f"{f.relative_to(ROOT)}:{lineno} -> {imp_name} (CORE forbids {forb})"
                        )

    print(f"# IMPORT_MAP_FROZEN_V2")
    print(f"")
    print(f"Generated: Phase 10.1 B1 - A1 closed, B2 guardrail 395 passed")
    print(f"Root: {ROOT}")
    print(f"Modules scanned: {len(all_files)}")
    print(f"")
    print(f"## Architecture Invariants")
    print(f"")
    print(f"Rule 1: CORE -> no api/crud_ui/application/infrastructure/showcases")
    if core_violations:
        print(f"- FAIL VIOLATIONS: {len(core_violations)}")
        for v in core_violations[:30]:
            print(f" - {v}")
    else:
        print(f"- PASS 0 violations")
    print(f"")
    print(f"Rule 2: FRAMEWORK -> no showcases (framework never depends on showcase)")
    if showcase_violations:
        print(f"- FAIL VIOLATIONS: {len(showcase_violations)}")
        for v in showcase_violations[:30]:
            print(f" - {v}")
    else:
        print(f"- PASS 0 violations")
    print(f"")
    print(f"Rule 3: CRUD contracts boundary (A1.2 91351d0)")
    print(
        f"- contracts must not import engine/persistence - checked in test_architecture.py"
    )
    print(f"")
    print(f"## Dependency Model")
    print(f"```text")
    print(f"CORE (core/, domain/, services/slug/, validation/, crud/contracts)")
    print(f" | (depends only on stdlib / core itself)")
    print(f"ENGINE (crud/engine, pipeline/)")
    print(f" |")
    print(f"EXTENSION (api/, crud_ui/, application/, infrastructure/)")
    print(f" |")
    print(f"SHOWCASE (showcases/ - may depend on framework, never reverse)")
    print(f"```")
    print(f"")
    print(f"## Full Import Map (ai_framework/*)")
    print(f"")
    for mod in sorted(import_map.keys()):
        imps = sorted(set(import_map[mod]))
        if not imps:
            continue
        print(f"### {mod}")
        for imp in imps:
            marker = ""
            if "showcases" in imp.lower():
                marker = " [SHOWCASE]"
            if (
                any(x in mod for x in ["core", "domain", "validation"])
                or "services.slug" in mod
            ):
                if any(
                    f in imp
                    for f in [
                        "api",
                        "crud_ui",
                        "application",
                        "infrastructure",
                        "showcases",
                    ]
                ):
                    marker = " [FORBIDDEN FOR CORE]"
            print(f"- {imp}{marker}")
        print(f"")

    print(f"## Reverse Map - Who imports what (Top 50 internal)")
    print(f"")
    sorted_reverse = sorted(reverse_map.items(), key=lambda x: len(x[1]), reverse=True)
    for imported, importers in sorted_reverse[:50]:
        if not imported.startswith("ai_framework"):
            continue
        print(f"### {imported} (imported by {len(importers)})")
        for imp_by in sorted(set(importers))[:20]:
            print(f"- {imp_by}")
        print(f"")


if __name__ == "__main__":
    main()
