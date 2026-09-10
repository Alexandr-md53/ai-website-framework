# CODING: utf-8, ASCII only
from pathlib import Path
import json
import re
import shutil

FRAMEWORK_VERSION = "10.2.0-c1"


def _framework_version() -> str:
    return FRAMEWORK_VERSION


def list_templates() -> list[str]:
    tmpl_root = Path(__file__).resolve().parents[1] / "templates"
    if not tmpl_root.exists():
        return []
    return [p.name for p in tmpl_root.iterdir() if p.is_dir()]


def _validate_name(name: str) -> str:
    normalized = name.strip()
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", normalized):
        raise ValueError(f"Invalid project name: {name}")
    return normalized


def scaffold_crud(
    name: str, dest_root: Path, description: str = "", with_example: bool = False
) -> Path:
    normalized = _validate_name(name)
    dest_root = Path(dest_root)
    dest = dest_root / normalized

    if dest.exists():
        raise FileExistsError(f"Destination {dest} already exists")

    tmpl_root = Path(__file__).resolve().parents[1] / "templates" / "crud"
    if not tmpl_root.exists():
        raise FileNotFoundError(f"Template root missing: {tmpl_root}")

    # create root
    dest.mkdir(parents=True, exist_ok=False)

    # create showcases/__init__.py - THIS answers your question where __init__.py is created
    # It is created AUTOMATICALLY here, not by you manually
    showcases_root = dest / "showcases"
    showcases_root.mkdir(parents=True, exist_ok=True)
    (showcases_root / "__init__.py").write_text("", encoding="utf-8")

    showcase_dir = showcases_root / normalized
    showcase_dir.mkdir(parents=True, exist_ok=True)

    for sub in ["domain", "metadata", "services"]:
        sub_path = showcase_dir / sub
        sub_path.mkdir(parents=True, exist_ok=True)
        (sub_path / "__init__.py").write_text("", encoding="utf-8")

    (showcase_dir / "__init__.py").write_text("", encoding="utf-8")

    # pyproject.toml from template
    pyproject_tmpl = tmpl_root / "pyproject.toml.tmpl"
    pyproject_text = pyproject_tmpl.read_text(encoding="utf-8")
    pyproject_text = pyproject_text.replace("{{name}}", normalized)
    pyproject_text = pyproject_text.replace("{{version}}", _framework_version())
    pyproject_text = pyproject_text.replace(
        "{{description}}", description or f"{normalized} crud"
    )
    (dest / "pyproject.toml").write_text(pyproject_text, encoding="utf-8")

    # manifest.json - single canonical in root (C4.2)
    manifest = {
        "product": "crud",
        "version": _framework_version(),
        "name": normalized,
        "description": description or f"{normalized} crud",
        "package": f"showcases.{normalized}",
        "domain": {"package": f"showcases.{normalized}.domain"},
        "metadata": {"package": f"showcases.{normalized}.metadata"},
        "services": {"package": f"showcases.{normalized}.services"},
    }
    if with_example:
        manifest["examples"] = ["example"]

    (dest / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    # C4.4 - example files, created ONLY if with_example=True
    # THIS is the file where you add the if with_example block - you already did it by replacing whole file
    if with_example:
        (showcase_dir / "domain" / "example.py").write_text(
            (tmpl_root / "domain" / "example.py.tmpl")
            .read_text(encoding="utf-8")
            .replace("{{name}}", normalized),
            encoding="utf-8",
        )
        (showcase_dir / "metadata" / "example.json").write_text(
            (tmpl_root / "metadata" / "example.json.tmpl")
            .read_text(encoding="utf-8")
            .replace("{{name}}", normalized),
            encoding="utf-8",
        )
        (showcase_dir / "services" / "example_service.py").write_text(
            (tmpl_root / "services" / "example_service.py.tmpl")
            .read_text(encoding="utf-8")
            .replace("{{name}}", normalized),
            encoding="utf-8",
        )

    return dest


def validate_scaffold(project_path: Path) -> list[str]:
    """C4.2 contract validator, C4.4 allows optional examples field."""
    errors = []
    project_path = Path(project_path)
    name = project_path.name

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

        pkg = data.get("package", "")
        if pkg and pkg != f"showcases.{name}":
            errors.append(f"package must be showcases.{name}, got {pkg}")

        if "examples" in data:
            if not isinstance(data["examples"], list):
                errors.append("manifest.examples must be a list")

    return errors


def inspect_project(project_path: Path) -> dict:
    project_path = Path(project_path)
    name = project_path.name
    showcase_dir = project_path / "showcases" / name
    result = {
        "valid": True,
        "errors": [],
        "manifest": None,
        "manifest_version": None,
        "pyproject_version": None,
        "framework_version": _framework_version(),
    }

    root_manifest = project_path / "manifest.json"
    if not root_manifest.exists():
        result["valid"] = False
        result["errors"].append("manifest.json missing")
        return result

    try:
        manifest = json.loads(root_manifest.read_text(encoding="utf-8"))
        result["manifest"] = manifest
        result["manifest_version"] = manifest.get("version")
    except Exception as e:
        result["valid"] = False
        result["errors"].append(f"manifest invalid: {e}")
        return result

    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8")
        import re as _re

        m = _re.search(r'version\s*=\s*["\']([^"\']+)["\']', text)
        if m:
            result["pyproject_version"] = m.group(1)

    examples = manifest.get("examples", [])
    if examples:
        for ex in examples:
            if not (showcase_dir / "domain" / f"{ex}.py").exists():
                result["errors"].append(f"missing domain/{ex}.py")
                result["valid"] = False
            if not (showcase_dir / "metadata" / f"{ex}.json").exists():
                result["errors"].append(f"missing metadata/{ex}.json")
                result["valid"] = False
            if not (showcase_dir / "services" / f"{ex}_service.py").exists():
                result["errors"].append(f"missing services/{ex}_service.py")
                result["valid"] = False

    return result
