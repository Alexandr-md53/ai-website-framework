Dependency Rules — Frozen
Source: AGENTS.md + docs/IMPORT_MAP_FROZEN_V2.md + tests/test_architecture.py

Rules
CORE must NOT import EXTENSION or SHOWCASE
ENGINE must NOT import api, showcases
EXTENSION may depend on CORE, ENGINE via public API only
SHOWCASE may depend on framework, reverse is forbidden
All imports from ai_framework.* — no from framework.* (checked via Get-ChildItem Select-String)
Verification
powershell
Get-ChildItem -Recurse -File -Include *.py | Select-String -Pattern "from\s+framework(\s|\.)|import\s+framework(\s|\.)" | Where-Object { $_.Line -notmatch "ai_framework" }
# → 0 results
Public API
ai_framework/crud/init.py: CRUDContext, CRUDResult, CRUDError, PersistenceProviderProtocol, UniversalCRUDEngine, CRUDEngine, InMemoryPersistenceProvider, SQLitePersistenceProvider
ai_framework/pipeline/init.py: single source Engine
ai_framework/api/init.py: single source Delivery Adapter
