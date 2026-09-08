# CODING: utf-8, ASCII only

"""CLI skeleton - C1 minimal, no CORE dependencies."""

import argparse
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib


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
    # verify = product contract, same as check for C1
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-framework",
        description="AI Website Framework CLI - C1 skeleton",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    # Product contract C1
    p_verify = sub.add_parser(
        "verify", help="Verify baseline 395 passed + architecture"
    )
    p_verify.set_defaults(func=cmd_verify)

    p_new = sub.add_parser("new", help="Scaffold new project (C1: only --list)")
    p_new.add_argument("--list", action="store_true", help="List available templates")
    p_new.set_defaults(func=cmd_new)

    # Internal / handoff contract - keep for compatibility
    p_check = sub.add_parser(
        "check", help="Run pytest -q and architecture guard (alias for verify)"
    )
    p_check.set_defaults(func=cmd_check)

    p_map = sub.add_parser("import-map", help="Regenerate docs/IMPORT_MAP_FROZEN_V2.md")
    p_map.set_defaults(func=cmd_import_map)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
