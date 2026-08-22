import ast
from pathlib import Path


FORBIDDEN_IMPORTS = {
    "flask",
    "fastapi",
    "sqlalchemy",
    "pydantic",
    "requests",
    "pytest",
    "telegram",
}

METADATA_DIR = Path(__file__).parent.parent.parent / "ai_framework" / "metadata"


def test_metadata_module_imports_are_isolated():
    """Ensure ai_framework.metadata has no dependencies on external web/ORM frameworks."""
    python_files = list(METADATA_DIR.glob("**/*.py"))
    assert len(python_files) > 0, f"No python files found in {METADATA_DIR}"

    violations = []

    for py_file in python_files:
        if py_file.name == "__init__.py":
            continue

        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))

        for node in ast.walk(tree):
            imported_module = None

            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_module = alias.name.split(".")[0]
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_module = node.module.split(".")[0]

            if imported_module in FORBIDDEN_IMPORTS:
                violations.append(
                    f"File '{py_file.name}' imports forbidden package '{imported_module}'"
                )

    assert not violations, "Architectural boundary violations found:\n" + "\n".join(
        violations
    )
