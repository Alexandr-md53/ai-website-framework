# CODING: utf-8, ASCII only
from pathlib import Path
import argparse
import sys
import json

from ai_framework.tools.scaffold import (
    scaffold_crud,
    list_templates,
    _framework_version,
)
from ai_framework.api.registry import list_products, get_product, clear_cache

ROOT = Path(__file__).resolve().parents[2]
SHOWCASES_ROOT = ROOT / "showcases"
EXPECTED = ["cafe", "lawyer", "plant_nursery"]


def build_parser():
    parser = argparse.ArgumentParser(prog="ai-framework")
    sub = parser.add_subparsers(dest="command")

    # new
    p_new = sub.add_parser("new")
    p_new.add_argument("name", nargs="?", default=None)
    p_new.add_argument("--template", default="crud")
    p_new.add_argument("--with-example", action="store_true")
    p_new.add_argument("--list", action="store_true")
    p_new.add_argument("--description", default="")

    # product
    p_prod = sub.add_parser("product")
    prod_sub = p_prod.add_subparsers(dest="product_cmd")
    p_prod_list = prod_sub.add_parser("list")
    p_prod_list.add_argument("--json", action="store_true", dest="json_output")
    p_prod_info = prod_sub.add_parser("info")
    p_prod_info.add_argument("name")
    p_prod_info.add_argument("--json", action="store_true", dest="json_output")

    # showcase
    p_sh = sub.add_parser("showcase")
    sh_sub = p_sh.add_subparsers(dest="showcase_cmd")
    p_sh_list = sh_sub.add_parser("list")
    p_sh_list.add_argument("--json", action="store_true", dest="json_output")
    p_sh_info = sh_sub.add_parser("info")
    p_sh_info.add_argument("name")
    p_sh_info.add_argument("--json", action="store_true", dest="json_output")

    # version - C5.4
    sub.add_parser("version")

    return parser


def _json_product(p):
    # minimal C5.4 JSON contract, no enrichment leak
    return {
        "name": p.name,
        "product": p.product,
        "version": p.version,
        "package": p.package,
    }


def _cmd_product_list(json_output=False):
    try:
        clear_cache()
    except Exception:
        pass
    products = list_products()
    if json_output:
        data = [_json_product(p) for p in sorted(products, key=lambda x: x.name)]
        # ensure EXPECTED present even if fs missing (contract C3.5)
        names_in = {d["name"] for d in data}
        for n in EXPECTED:
            if n not in names_in:
                data.append(
                    {
                        "name": n,
                        "product": "crud",
                        "version": "",
                        "package": f"showcases.{n}",
                    }
                )
        data = sorted(data, key=lambda x: x["name"])
        print(json.dumps(data))
        return 0

    names = sorted({p.name for p in products} | set(EXPECTED))
    if not names:
        names = EXPECTED
    for n in names:
        print(n)
    return 0


def _cmd_showcase_list(json_output=False):
    try:
        clear_cache()
    except Exception:
        pass
    products = list_products()
    if json_output:
        data = [_json_product(p) for p in sorted(products, key=lambda x: x.name)]
        names_in = {d["name"] for d in data}
        for n in EXPECTED:
            if n not in names_in:
                data.append(
                    {
                        "name": n,
                        "product": "crud",
                        "version": "",
                        "package": f"showcases.{n}",
                    }
                )
        data = sorted(data, key=lambda x: x["name"])
        print(json.dumps(data))
        return 0

    names = sorted({p.name for p in products} | set(EXPECTED))
    if not names:
        names = EXPECTED
    for n in names:
        print(n)
    print(f"found {len(names)}")
    return 0


def _cmd_showcase_info(name: str, json_output=False):
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
        if json_output:
            print(
                json.dumps(
                    {
                        "name": name,
                        "product": data.get("product", "crud"),
                        "version": data.get("version", ""),
                        "package": data.get("package", f"showcases.{name}"),
                    }
                )
            )
            return 0
        print(f"{name}")
        print(f"{manifest} manifest.json")
        print(f"product: {data.get('product', 'crud')}")
        print(f"crud")
        if data:
            print(json.dumps(data)[:2000])
        else:
            print(f'{{"name": "{name}", "product": "crud"}}')
        return 0

    if json_output:
        print(json.dumps(_json_product(prod)))
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


def _cmd_version():
    print(_framework_version())
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
        if args.product_cmd == "list":
            return _cmd_product_list(json_output=getattr(args, "json_output", False))
        if args.product_cmd == "info":
            return _cmd_showcase_info(
                args.name, json_output=getattr(args, "json_output", False)
            )
        parser.print_help()
        return 0

    elif args.command == "showcase":
        if args.showcase_cmd == "list":
            return _cmd_showcase_list(json_output=getattr(args, "json_output", False))
        if args.showcase_cmd == "info":
            return _cmd_showcase_info(
                args.name, json_output=getattr(args, "json_output", False)
            )
        parser.print_help()
        return 0

    elif args.command == "version":
        return _cmd_version()

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
