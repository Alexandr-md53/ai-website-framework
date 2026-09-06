START_HERE.md — AI Website Framework — Phase 9.1 Frozen v2
Entry point for agents and developers. Read this first.

Current State: Phase 9.1 Frozen v2 — 2026-09-05
Status: CANONICAL GREEN [100%] — Zero Legacy

This is the frozen canonical version after full removal of the old generation framework/.

What is this project?
AI Website Framework — generates complete static websites via AI pipeline:
UseCases → Pipeline → CRUD → AssetManager → Publisher

Core package: ai_framework/ — the only source of truth. No framework/ exists.

Canonical Structure (frozen v2)
ai_framework/          # canonical core (only implementation)
  ai_provider/         # AI adapters, contracts
  api/                 # API adapter, contracts, endpoint
  application/         # DTOs, pipeline (contracts, adapter, executor), use_cases
  asset_manager/       # contracts, manager, storage
  core/                # core package (CRUD wrappers)
  crud/                # engine, persistence, contracts
  domain/              # value_objects, entities, contracts, exceptions
  publisher/           # publisher core
  plugins/             # plugin contracts (inside ai_framework)
  services/            # slug, etc.
  __init__.py
docs/
plugins/               # empty (external plugins placeholder, legacy telegram removed)
showcases/             # example showcases
tests/                 # 392 tests — canonical only
pyproject.toml
pytest.ini
.gitignore
AGENTS.md
README.md
CHANGELOG.md
START_HERE.md          # this file
CHAT_BOOTSTRAP.md
Important: plugins/ is empty intentionally. Legacy plugins/telegram/publisher.py was removed (see below). Keep empty or add .gitkeep if git requires it.

Phase 9.1 — What was done (2026-09-05)
This phase completes the Zero Domain Knowledge cleanup defined in AGENTS.md.

Step 2: Removed framework/
Deleted entire directory framework/ (old generation)
Result: 11 test collection errors (expected)
Step 3: Removed 11 legacy tests
Deleted tests that imported from removed framework/:

test_framework_*
test_ai_website_generator*
test_image_processor*
test_political_bias*
test_website_templates
Result: pytest collection 0 errors
Step 4: Fixed slug_orchestrator.py
File: ai_framework/application/pipeline/slug_orchestrator.py
Before:

python
from framework.core.slug import SlugGenerator  # legacy, broken encoding
After (canonical):

python
from ai_framework.services.slug import SlugGenerator, DefaultCollisionResolver
Verification: python -m pytest -q → GREEN [100%]

Step 5: Removed last legacy tail plugins/telegram/
File: plugins/telegram/publisher.py
Classification: LEGACY

from framework.core.contracts import PublisherPluginContract
from framework.core.exceptions import ...
Old interface get_metadata(), validate(), publish() with requests
Broken encoding ÐŸÐ»Ð°Ð³Ð¸Ð½...
Action: Remove-Item -Recurse -Force plugins/telegram
Result: dir plugins → empty, dir plugins/telegram → not found

Step 5.1: Residual check and final regression
Commands executed:

powershell
# Must return 0 results (excludes ai_framework)
Get-ChildItem -Recurse -File -Include *.py | Select-String -Pattern "from\s+framework(\s|\.)|import\s+framework(\s|\.)" | Where-Object { $_.Line -notmatch "ai_framework" }
# → empty — proof of full legacy removal

python -m pytest -q
# → ........................................................................
# → [100%] GREEN
Dump artifacts removed:

TREE_FROZEN.txt, DUMP_FROZEN.txt, IMPORT_MAP.txt
framework_inventory_before.txt, framework_inventory_after.txt
git_status_before.txt, pytest_after_framework_delete.txt, remaining_framework_imports.txt
Final verification criteria (all met)
✅ framework/ deleted
✅ 11 legacy tests deleted
✅ plugins/telegram deleted (last legacy plugin)
✅ slug_orchestrator.py fixed to canonical import
✅ 0 residual from framework / import framework (excluding ai_framework)
✅ pytest -q GREEN [100%] — ~392 passed (exact count from pytest -q output)
✅ Modern ai_framework/ works independently
How to run
powershell
# Install
pip install -e .

# Tests
python -m pytest -q
python -m pytest -q --tb=short

# Check legacy residues (should be empty)
Get-ChildItem -Recurse -File -Include *.py | Select-String -Pattern "from\s+framework(\s|\.)|import\s+framework(\s|\.)" | Where-Object { $_.Line -notmatch "ai_framework" }
Rules (from AGENTS.md)
Zero Domain Knowledge — no domain logic in framework
Single source of truth — only ai_framework/
No framework/ directory — deleted in Phase 9.1
All imports must be from ai_framework.*
Plugins outside ai_framework/plugins/contracts.py are external and must not import from framework
Next steps after Frozen v2
Use this folder ai-website-framework -copi-git as main project
Delete old folder ai-website-framework (containing framework/)
Push to git:
powershell
git add -A
git commit -m "phase-9-frozen-v2: remove legacy framework/ + 11 tests + plugins/telegram, fix slug_orchestrator canonical import, pytest GREEN 100%"
git push
References
AGENTS.md — agent instructions and Zero Domain Knowledge
CHANGELOG.md — version history including Phase 9.1
README.md — project overview
CHAT_BOOTSTRAP.md — bootstrap for chat agents
Generated: 2026-09-05 — Phase 9.1 Frozen v2

