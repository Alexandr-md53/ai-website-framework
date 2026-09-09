# CODING: utf-8, ASCII only
"""C4.1/C4.2 - crud template scaffolding, single canonical manifest."""

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


def _framework_version() -> str:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    pyproject = _project_root() / "pyproject.toml"
    with pyproject.open("rb") as f:
        return tomllib.load(f)["project"]["version"]


def scaffold_crud(name: str, dest_root: Path, description: str = "") -> Path:
    raw = name.strip()
    normalized = raw.lower().replace("-", "_")
    if not normalized.isidentifier():
        raise ValueError(
            f"invalid project name '{raw}' -> '{normalized}' must be identifier"
        )
    dest = Path(dest_root)
    if dest.exists() and dest.is_dir() and dest.name != normalized:
        dest = dest / normalized
    dest.mkdir(parents=True, exist_ok=True)

    ctx = {
        "name": normalized,
        "Name": normalized.capitalize(),
        "description": description or f"{normalized} crud showcase",
        "version": _framework_version(),
    }

    t_root = _project_root() / "ai_framework" / "templates" / "crud"
    if not t_root.exists():
        raise FileNotFoundError(f"template not found: {t_root}")

    # ONLY root tmpl files -> single canonical manifest
    for tmpl_file in t_root.glob("*.tmpl"):
        out_name = tmpl_file.name.replace(".tmpl", "")
        rendered = _render(tmpl_file.read_text(encoding="utf-8"), ctx)
        (dest / out_name).write_text(rendered, encoding="utf-8")

    # showcases/<name>/ with code skeleton, NO manifest.json inside
    showcase_dir = dest / "showcases" / normalized
    showcase_dir.mkdir(parents=True, exist_ok=True)
    (showcase_dir / "__init__.py").write_text("", encoding="utf-8")

    for sub in ["domain", "metadata", "services"]:
        sub_dir = showcase_dir / sub
        sub_dir.mkdir(exist_ok=True)
        (sub_dir / "__init__.py").write_text("", encoding="utf-8")

    return dest


def validate_scaffold(project_path: Path) -> list[str]:
    """C4.2 contract validator."""
    errors = []
    project_path = Path(project_path)
    name = project_path.name

    # single manifest rule
    root_manifest = project_path / "manifest.json"
    nested_manifest = project_path / "showcases" / name / "manifest.json"

    if not root_manifest.exists():
        errors.append("manifest.json missing in project root (canonical)")
    if nested_manifest.exists():
        errors.append(
            f"duplicate manifest forbidden: {nested_manifest} must not exist (C4.2)"
        )

    if root_manifest.exists():
        try:
            data = json.loads(root_manifest.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append(f"manifest.json invalid JSON: {e}")
            return errors

        # minimal contract
        if data.get("product") != "crud":
            errors.append(f"product must be 'crud', got {data.get('product')}")
        if data.get("name") != name:
            errors.append(f"manifest.name '{data.get('name')}'!= dir '{name}'")
        if data.get("version") != _framework_version():
            errors.append(
                f"version mismatch: {data.get('version')}!= {_framework_version()}"
            )
        for field in ["domain", "metadata", "services"]:
            if not data.get(field):
                errors.append(f"manifest.{field} empty or missing")
        if not (project_path / "pyproject.toml").exists():
            errors.append("pyproject.toml missing")

        # filesystem compatibility - package/path согласованность
        pkg = data.get("package", "")
        if pkg and pkg != f"showcases.{name}":
            errors.append(f"package must be showcases.{name}, got {pkg}")

    return errors
