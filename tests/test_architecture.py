"""
B2: Architecture Rule Linter - minimal guardrail
Phase 10.1 A1 closed -> lock architecture automatically

Rules:
1. CORE (core/, domain/, services/slug/, validation/) must NOT import:
   - api, crud_ui, application, infrastructure, showcases
   CORE is pure domain logic, no Delivery, no App, no Infra, no Showcase.

2. FRAMEWORK never depends on SHOWCASE
   ai_framework/* must NOT import showcases / ai_framework/showcases
   Showcase MAY depend on framework (allowed), reverse forbidden.

Baseline: 392 tests must stay GREEN.
This test adds 2 more -> 394 expected.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).parent.parent
AI_FRAMEWORK = ROOT / "ai_framework"

# ---- CORE definition ----
CORE_DIRS = [
    AI_FRAMEWORK / "core",
    AI_FRAMEWORK / "domain",
    AI_FRAMEWORK / "services" / "slug",
    AI_FRAMEWORK / "validation",
    # CRUD Engine/Provider is also CORE by nature, but A1.2 defines its own boundary
    # We include it as CORE for extra safety, if exists
    AI_FRAMEWORK / "crud" / "contracts",
]

# Forbidden imports for CORE
FORBIDDEN_FOR_CORE = [
    "ai_framework.api",
    "ai_framework.crud_ui",
    "ai_framework.application",
    "ai_framework.infrastructure",
    "ai_framework.showcases",
    "showcases",
    # short forms that appear in from X import
    "api",
    "crud_ui",
    "infrastructure",
]

# For rule 2: framework must not import showcase at all
FORBIDDEN_SHOWCASE_PATTERNS = [
    "showcases",
    "ai_framework.showcases",
]


def iter_py_files(base: Path):
    if not base.exists():
        return []
    if base.is_file() and base.suffix == ".py":
        return [base]
    return list(base.rglob("*.py"))


def get_imports_from_file(py_file: Path) -> list[str]:
    """Return list of imported module strings via AST."""
    try:
        source = py_file.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(py_file))
    except Exception:
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
            # also check level? relative imports: we keep module name
    return imports


def test_core_no_forbidden_dependencies():
    """
    CORE
     ├─ core/
     ├─ domain/
     ├─ services/slug/
     └─ validation/
           │
           ├── ❌ api
           ├── ❌ crud_ui
           ├── ❌ application
           ├── ❌ infrastructure
           └── ❌ showcases
    """
    violations = []

    core_files = []
    for d in CORE_DIRS:
        core_files.extend(iter_py_files(d))

    # Also include ai_framework/core, domain, validation dirs fully if they exist
    for extra in [
        AI_FRAMEWORK / "core",
        AI_FRAMEWORK / "domain",
        AI_FRAMEWORK / "validation",
        AI_FRAMEWORK / "services" / "slug",
    ]:
        if extra.exists():
            core_files.extend(iter_py_files(extra))

    # dedup
    core_files = list(set(core_files))

    if not core_files:
        # If CORE dirs don't exist yet in this repo variant, test passes as guardrail placeholder
        return

    for f in core_files:
        # skip __pycache__
        if "__pycache__" in str(f):
            continue
        imports = get_imports_from_file(f)
        for imp in imports:
            imp_low = imp.lower()
            for forbidden in FORBIDDEN_FOR_CORE:
                # exact match or submodule: forbidden == imp or imp startswith forbidden + "."
                if (
                    imp_low == forbidden
                    or imp_low.startswith(forbidden + ".")
                    or forbidden in imp_low.split(".")
                ):
                    # Special case: allow ai_framework.api.contracts inside api itself, but not in CORE
                    # For CORE, any mention of api/crud_ui/application/infrastructure/showcases is forbidden
                    # We check if file is inside CORE and import is forbidden layer
                    # Exclude self-imports (e.g., core importing core)
                    if (
                        "ai_framework.api" in imp_low
                        or "ai_framework.crud_ui" in imp_low
                        or "ai_framework.application" in imp_low
                        or "ai_framework.infrastructure" in imp_low
                        or "showcases" in imp_low
                    ):
                        violations.append(
                            f"{f.relative_to(ROOT)} imports forbidden '{imp}' (rule: CORE -> {forbidden} forbidden)"
                        )
                    elif forbidden in [
                        "api",
                        "crud_ui",
                        "application",
                        "infrastructure",
                    ] and imp_low.startswith(forbidden):
                        violations.append(
                            f"{f.relative_to(ROOT)} imports forbidden '{imp}'"
                        )

    if violations:
        msg = (
            "CORE layer violations (core/domain/services/slug/validation must not depend on api/crud_ui/application/infrastructure/showcases):\n"
            + "\n".join(f"  - {v}" for v in sorted(set(violations))[:50])
        )
        assert False, msg


def test_framework_never_depends_on_showcase():
    """
    CORE / EXTENSION
            │
            └── ❌ showcases

    Showcase may depend on framework, but framework never depends on Showcase.
    ai_framework/* must not import showcases.
    """
    violations = []

    if not AI_FRAMEWORK.exists():
        return

    all_framework_files = [
        p for p in AI_FRAMEWORK.rglob("*.py") if "__pycache__" not in str(p)
    ]

    for f in all_framework_files:
        # Skip showcases folder itself - it IS allowed to import itself
        if "showcases" in f.parts:
            continue
        imports = get_imports_from_file(f)
        for imp in imports:
            imp_low = imp.lower()
            for pattern in FORBIDDEN_SHOWCASE_PATTERNS:
                if pattern in imp_low:
                    violations.append(
                        f"{f.relative_to(ROOT)} -> imports '{imp}' (framework must not depend on showcases)"
                    )

    if violations:
        msg = (
            "FRAMEWORK -> SHOWCASE dependency violations (framework must never import showcases):\n"
            + "\n".join(f"  - {v}" for v in sorted(set(violations))[:50])
        )
        assert False, msg


def test_crud_boundary_still_respected():
    """
    Extra guardrail from A1.2: crud/contracts must not import engine or persistence
    This locks the 91351d0 fix.
    """
    contracts_file = AI_FRAMEWORK / "crud" / "contracts.py"
    if not contracts_file.exists():
        return

    imports = get_imports_from_file(contracts_file)
    forbidden = [
        "ai_framework.crud.engine",
        "ai_framework.crud.crud_engine",
        "ai_framework.crud.persistence",
        "ai_framework.crud.sqlite_persistence",
    ]

    violations = [imp for imp in imports if any(f in imp for f in forbidden)]

    if violations:
        assert False, (
            f"crud/contracts.py must not import engine/persistence (A1.2 boundary broken): {violations}"
        )
