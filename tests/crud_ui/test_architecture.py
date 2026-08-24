import ast
from pathlib import Path


def test_crud_ui_has_no_forbidden_imports():
    crud_ui_dir = Path("ai_framework/crud_ui")
    if not crud_ui_dir.exists():
        return

    forbidden_modules = {
        "flask",
        "fastapi",
        "jinja2",
        "sqlalchemy",
        "ai_framework.domain",
        "ai_framework.application",
        "ai_framework.infrastructure",
    }

    for py_file in crud_ui_dir.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_modules:
                        assert not alias.name.startswith(forbidden), (
                            f"Forbidden import {alias.name} in {py_file}"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for forbidden in forbidden_modules:
                        assert not node.module.startswith(forbidden), (
                            f"Forbidden import from {node.module} in {py_file}"
                        )
