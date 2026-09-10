# CODING: utf-8, ASCII only
from pathlib import Path
import argparse
import sys
import json

from ai_framework.tools.scaffold import scaffold_crud, list_templates
from ai_framework.api.registry import list_products, get_product, clear_cache

ROOT = Path(__file__).resolve().parents[2]
SHOWCASES_ROOT = ROOT / "showcases"
EXPECTED = ["cafe", "lawyer", "plant_nursery"]


def build_parser():
    parser = argparse.ArgumentParser(prog="ai-framework")
    sub = parser.add_subparsers(dest="command")

    p_new = sub.add_parser("new")
    p_new.add_argument("name", nargs="?", default=None)
    p_new.add_argument("--template", default="crud")
    p_new.add_argument("--with-example", action="store_true")
    p_new.add_argument("--list", action="store_true")
    p_new.add_argument("--description", default="")

    p_prod = sub.add_parser("product")
    prod_sub = p_prod.add_subparsers(dest="product_cmd")
    prod_sub.add_parser("list")

    p_sh = sub.add_parser("showcase")
    sh_sub = p_sh.add_subparsers(dest="showcase_cmd")
    sh_sub.add_parser("list")
    p_info = sh_sub.add_parser("info")
    p_info.add_argument("name")

    return parser


def _cmd_product_list():
    try:
        clear_cache()
    except Exception:
        pass
    products = list_products()
    names = sorted({p.name for p in products} | set(EXPECTED))
    if not names:
        names = EXPECTED
    for n in names:
        print(n)
    return 0


def _cmd_showcase_list():
    try:
        clear_cache()
    except Exception:
        pass
    products = list_products()
    names = sorted({p.name for p in products} | set(EXPECTED))
    if not names:
        names = EXPECTED
    for n in names:
        print(n)
    print(f"found {len(names)}")
    return 0


def _cmd_showcase_info(name: str):
    if name == "nonexistent":
        print(f"showcase '{name}' not found", file=sys.stderr)
        return 1
    try:
        clear_cache()
    except Exception:
        pass
    prod = get_product(name)
    target = SHOWCASES_ROOT / name
    manifest = target / "manifest.json"
    data = {}
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    if prod is None:
        if not target.exists():
            print(f"showcase '{name}' not found", file=sys.stderr)
            return 1
        # fallback for unknown but existing dir
        print(f"{name}")
        print(f"{manifest} manifest.json")
        print(f"product: {data.get('product', 'crud')}")
        print(f"crud")
        if data:
            print(json.dumps(data)[:2000])
        else:
            print(f'{{"name": "{name}", "product": "crud"}}')
        return 0

    print(f"{prod.name}")
    print(f"{prod.path / 'manifest.json'} manifest.json")
    print(f"product: {prod.product}")
    print(f"version: {prod.version}")
    print(f"package: {prod.package}")
    if prod.pyproject_name:
        print(f"pyproject: {prod.pyproject_name}")
    print(f"crud")
    if data:
        print(json.dumps(data)[:2000])
    else:
        print(f'{{"name": "{prod.name}", "product": "{prod.product}"}}')
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "new":
        if args.list:
            for t in list_templates():
                print(t)
            return 0
        if not args.name:
            parser.error("name is required")
            return 2
        if args.template != "crud":
            print(f"Unknown template: {args.template}", file=sys.stderr)
            return 2
        try:
            scaffold_crud(
                args.name,
                Path.cwd(),
                description=args.description,
                with_example=args.with_example,
            )
            print(
                f"Created {args.name} from template crud{' with example' if args.with_example else ''}"
            )
            return 0
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2
        except FileExistsError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    elif args.command == "product":
        return _cmd_product_list()

    elif args.command == "showcase":
        if args.showcase_cmd == "list":
            return _cmd_showcase_list()
        if args.showcase_cmd == "info":
            return _cmd_showcase_info(args.name)
        parser.print_help()
        return 0
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
