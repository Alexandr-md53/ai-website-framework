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
    showcases_root = dest / "showcases"
    showcases_root.mkdir(parents=True, exist_ok=True)
    (showcases_root / "__init__.py").write_text("", encoding="utf-8")

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


def _read_pyproject_toml(project_path: Path) -> dict:
    """Filesystem-only read of pyproject.toml, no import of generated code."""
    project_path = Path(project_path)
    pyproject = project_path / "pyproject.toml"
    if not pyproject.exists():
        return {}
    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        with pyproject.open("rb") as f:
            return tomllib.load(f)
    except Exception:
        # fallback simple parse for name/version only
        try:
            text = pyproject.read_text(encoding="utf-8")
            return {"raw_text": text}
        except Exception:
            return {}


def inspect_project(project_path: Path) -> dict:
    """
    C4.3: filesystem-only inspection of generated CRUD artifact.
    C4.3 MUST NOT dynamically load generated pkg or rely on importlib.
    Only Path / json / toml allowed for inspection.
    """
    project_path = Path(project_path)
    name = project_path.name
    errors: list[str] = []

    manifest_path = project_path / "manifest.json"
    pyproject_path = project_path / "pyproject.toml"

    manifest_data: dict = {}
    if not manifest_path.exists():
        errors.append("manifest.json missing in project root")
    else:
        try:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append(f"manifest.json invalid: {e}")
            manifest_data = {}

    pyproject_data = _read_pyproject_toml(project_path)
    if not pyproject_path.exists():
        errors.append("pyproject.toml missing")

    # filesystem structure checks (no import)
    showcase_pkg_dir = project_path / "showcases" / name
    if not showcase_pkg_dir.exists():
        errors.append(f"showcases/{name} missing")
    for sub in ["", "domain", "metadata", "services"]:
        p = (
            showcase_pkg_dir / sub / "__init__.py"
            if sub
            else showcase_pkg_dir / "__init__.py"
        )
        if not p.exists():
            errors.append(f"{p.relative_to(project_path)} missing")

    # forbidden nested manifest (C4.2)
    nested = project_path / "showcases" / name / "manifest.json"
    if nested.exists():
        errors.append(f"duplicate manifest forbidden: {nested}")

    # manifest ↔ filesystem consistency (still filesystem-only)
    if manifest_data:
        if manifest_data.get("name") != name:
            errors.append(
                f"manifest.name mismatch: {manifest_data.get('name')}!= {name}"
            )
        if manifest_data.get("product") != "crud":
            errors.append(f"manifest.product must be crud")
        pkg = manifest_data.get("package", "")
        if pkg != f"showcases.{name}":
            errors.append(f"manifest.package must be showcases.{name}, got {pkg}")
        # metadata/services startswith package
        md = manifest_data.get("metadata", "")
        if md and not md.startswith(f"showcases.{name}"):
            errors.append(f"metadata must start with showcases.{name}: {md}")
        for svc in manifest_data.get("services", []):
            if not svc.startswith(f"showcases.{name}"):
                errors.append(f"service must start with showcases.{name}: {svc}")

    # version lock (filesystem)
    manifest_version = manifest_data.get("version") if manifest_data else None
    pyproject_version = None
    if isinstance(pyproject_data, dict):
        pyproject_version = (
            pyproject_data.get("project", {}).get("version")
            if "project" in pyproject_data
            else None
        )

    if manifest_version and pyproject_version and manifest_version != pyproject_version:
        errors.append(
            f"version lock failed: manifest {manifest_version}!= pyproject {pyproject_version}"
        )

    try:
        fw_version = _framework_version()
        if manifest_version and manifest_version != fw_version:
            errors.append(
                f"manifest.version {manifest_version}!= FRAMEWORK_VERSION {fw_version}"
            )
    except Exception:
        pass

    return {
        "path": str(project_path),
        "name": name,
        "manifest": manifest_data,
        "pyproject": pyproject_data,
        "manifest_version": manifest_version,
        "pyproject_version": pyproject_version,
        "errors": errors,
        "valid": len(errors) == 0,
    }
