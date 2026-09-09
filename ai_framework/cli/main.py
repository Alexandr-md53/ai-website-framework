# CODING: utf-8, ASCII only

"""CLI skeleton - C1 minimal + C3.4 product/showcase read-only hooks."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from ai_framework.product_registry import (
    discover_showcases,
    framework_manifest,
    get_showcase,
)


def _get_version() -> str:
    root = Path(__file__).resolve().parents[2]
    with (root / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)["project"]["version"]


VERSION = _get_version()


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_pytest(extra_args=None) -> int:
    root = _project_root()
    cmd = [sys.executable, "-m", "pytest", "-q"]
    if extra_args:
        cmd.extend(extra_args)
    result = subprocess.run(cmd, cwd=str(root))
    return result.returncode


def cmd_check(args: argparse.Namespace) -> int:
    root = _project_root()
    print(f"[check] project root: {root}")
    print("[check] running pytest -q...")
    rc = _run_pytest()
    if rc != 0:
        print("[check] pytest FAILED")
        return rc
    print("[check] running tests/test_architecture.py...")
    rc2 = _run_pytest(["tests/test_architecture.py"])
    if rc2 != 0:
        print("[check] architecture tests FAILED")
        return rc2
    print("[check] OK - 395+ passed expected")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    print("[verify] starting full verification...")
    rc = cmd_check(args)
    if rc != 0:
        return rc
    print("[verify] GREEN - baseline preserved")
    return 0


def cmd_import_map(args: argparse.Namespace) -> int:
    root = _project_root()
    docs_dir = root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    out_file = docs_dir / "IMPORT_MAP_FROZEN_V2.md"
    print(f"[import-map] generating {out_file}")
    result = subprocess.run(
        [sys.executable, "-m", "ai_framework.tools.import_map"],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        print("[import-map] FAILED")
        return result.returncode
    out_file.write_text(result.stdout, encoding="utf-8")
    print(f"[import-map] written: {out_file}")
    return 0


def cmd_new(args: argparse.Namespace) -> int:
    if args.list:
        print("[new] available templates:")
        print(" - minimal")
        print(" - crud-api")
        print(" - showcase")
        print("[new] (C1 skeleton - only --list implemented)")
        return 0
    print("[new] use: ai-framework new --list")
    print("[new] (full scaffolding will be in C2/C3)")
    return 0


def cmd_product_list(args: argparse.Namespace) -> int:
    fm = framework_manifest()
    if fm:
        print(
            f"[product] framework: {fm.get('name', 'ai-framework')} v{fm.get('version', '')}"
        )
        print(f" description: {fm.get('description', '')}")
    else:
        print(
            f"[product] framework v{VERSION} (manifest.json not found, using pyproject.toml)"
        )
    showcases = discover_showcases()
    print(f"[product] showcases: {len(showcases)}")
    for s in showcases:
        m = s.manifest
        print(
            f" - {s.name}: {m.get('description', '')} [{m.get('version', '')}] product={m.get('product', '')}"
        )
    return 0


def cmd_showcase_list(args: argparse.Namespace) -> int:
    showcases = discover_showcases()
    if not showcases:
        print("[showcase] no showcases found (expected showcases/*/manifest.json)")
        return 0
    print(f"[showcase] found {len(showcases)}:")
    for s in showcases:
        m = s.manifest
        print(
            f" - {s.name:20s} v{m.get('version', ''):12s} {m.get('product', ''):8s} {m.get('description', '')}"
        )
    return 0


def cmd_showcase_info(args: argparse.Namespace) -> int:
    info = get_showcase(args.name)
    if not info:
        print(f"[showcase] not found: {args.name}")
        print("[showcase] available:")
        for s in discover_showcases():
            print(f" - {s.name}")
        return 1
    print(f"[showcase] {info.name}")
    print(f" path: {info.path}")
    print(json.dumps(info.manifest, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-framework",
        description="AI Website Framework CLI - C1+C3.4",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_verify = sub.add_parser(
        "verify", help="Verify baseline 395 passed + architecture"
    )
    p_verify.set_defaults(func=cmd_verify)

    p_new = sub.add_parser("new", help="Scaffold new project (C1: only --list)")
    p_new.add_argument("--list", action="store_true", help="List available templates")
    p_new.set_defaults(func=cmd_new)

    p_check = sub.add_parser("check", help="Run pytest -q and architecture guard")
    p_check.set_defaults(func=cmd_check)

    p_map = sub.add_parser("import-map", help="Regenerate docs/IMPORT_MAP_FROZEN_V2.md")
    p_map.set_defaults(func=cmd_import_map)

    # C3.4 - product/showcase read-only hooks
    p_product = sub.add_parser("product", help="Product/showcase info (C3.4 read-only)")
    prod_sub = p_product.add_subparsers(dest="product_cmd", required=True)
    p_plist = prod_sub.add_parser(
        "list", help="List framework + showcases from filesystem"
    )
    p_plist.set_defaults(func=cmd_product_list)

    p_show = sub.add_parser("showcase", help="Showcase discovery via filesystem")
    show_sub = p_show.add_subparsers(dest="showcase_cmd", required=True)
    p_slist = show_sub.add_parser(
        "list", help="List showcases from showcases/*/manifest.json"
    )
    p_slist.set_defaults(func=cmd_showcase_list)
    p_sinfo = show_sub.add_parser("info", help="Show showcase manifest")
    p_sinfo.add_argument("name", help="Showcase name (cafe, lawyer, plant_nursery)")
    p_sinfo.set_defaults(func=cmd_showcase_info)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
