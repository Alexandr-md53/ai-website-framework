# CODING: utf-8, ASCII only
"""C4.1 - crud template scaffolding, filesystem only, no CORE imports."""

from pathlib import Path
import json


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _render(text: str, ctx: dict) -> str:
    for k, v in ctx.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


def list_templates() -> list:
    t_root = _project_root() / "ai_framework" / "templates"
    if not t_root.exists():
        return []
    return sorted([p.name for p in t_root.iterdir() if p.is_dir()])


def scaffold_crud(name: str, dest_root: Path, description: str = "") -> Path:
    raw = name.strip()
    normalized = raw.lower().replace("-", "_")
    if not normalized.isidentifier():
        raise ValueError(
            f"invalid project name '{raw}' -> '{normalized}' must be identifier"
        )
    dest = Path(dest_root)
    # if dest is existing dir and not named same, create subdir
    if dest.exists() and dest.is_dir() and dest.name != normalized:
        dest = dest / normalized
    dest.mkdir(parents=True, exist_ok=True)

    ctx = {
        "name": normalized,
        "Name": normalized.capitalize(),
        "description": description or f"{normalized} crud showcase",
    }

    t_root = _project_root() / "ai_framework" / "templates" / "crud"
    if not t_root.exists():
        raise FileNotFoundError(f"template not found: {t_root}")

    for tmpl_file in t_root.glob("*.tmpl"):
        out_name = tmpl_file.name.replace(".tmpl", "")
        rendered = _render(tmpl_file.read_text(encoding="utf-8"), ctx)
        (dest / out_name).write_text(rendered, encoding="utf-8")

    showcase_dir = dest / "showcases" / normalized
    showcase_dir.mkdir(parents=True, exist_ok=True)
    (showcase_dir / "__init__.py").write_text("", encoding="utf-8")

    manifest = {
        "name": normalized,
        "product": "crud",
        "version": "10.2.0-c1",
        "package": f"showcases.{normalized}",
        "description": ctx["description"],
        "domain": [f"{normalized}_item"],
        "metadata": f"showcases.{normalized}.metadata.{normalized}_metadata.get_{normalized}_item_ui_schema",
        "services": [
            f"showcases.{normalized}.services.{normalized}_service.{ctx['Name']}Service"
        ],
    }
    (showcase_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    for sub in ["domain", "metadata", "services"]:
        sub_dir = showcase_dir / sub
        sub_dir.mkdir(exist_ok=True)
        (sub_dir / "__init__.py").write_text("", encoding="utf-8")

    return dest
