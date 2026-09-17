Phase 9 - Business Showcases Frozen / Phase 9.1 Frozen v2
Tag: phase-9-frozen-v2
Date: 2026-09-05
Status: CANONICAL GREEN 100% - Zero Legacy
Tests: 392 passed (after removal), 444 GREEN in README

What is Phase 9
AI Website Framework generates complete static websites via pipeline:
UseCases -> Pipeline -> CRUD -> AssetManager -> Publisher
Core package: ai_framework/ - only source of truth. No framework/ exists.

Phase 9.1 Steps (from START_HERE.md)
Step 2: Removed framework/ - entire legacy directory deleted
Result: 11 test collection errors (expected)

Step 3: Removed 11 legacy tests:
test_framework_*
test_ai_website_generator*
test_image_processor*
test_political_bias*
test_website_templates
Result: pytest collection 0 errors

Step 4: Fixed slug_orchestrator.py
Before: from framework.core.slug import SlugGenerator
After: from ai_framework.services.slug import SlugGenerator, DefaultCollisionResolver

Step 5: Removed last legacy tail plugins/telegram/
Action: Remove-Item -Recurse -Force plugins/telegram
Result: plugins/ empty intentional

Step 5.1: Residual check
Get-ChildItem -Recurse -File -Include *.py | Select-String -Pattern "from\s+framework(\s|.)|import\s+framework(\s|.)" | Where-Object { $_.Line -notmatch "ai_framework" }
-> empty

python -m pytest -q
-> [100%] GREEN ~392 passed

Verification Criteria (all met)

framework/ deleted
11 legacy tests deleted
plugins/telegram deleted
slug_orchestrator.py fixed to canonical import
0 residual from framework / import framework
pytest -q GREEN 100%
Modern ai_framework/ works independently
Structure after cleanup
ai_framework/
docs/
plugins/ (empty placeholder)
showcases/
tests/
pyproject.toml, pytest.ini, .gitignore
AGENTS.md, README.md, CHANGELOG.md, START_HERE.md, CHAT_BOOTSTRAP.md

Showcases proven in Phase 9

Plant Nursery Showcase: Hierarchy, Media assets, Inventory, Search criteria
Cafe Showcase: Dynamic UI Metadata, Status Lifecycle, Price Modifiers, RBAC
Lawyer/Service Showcase: M2M Graphs, Complex Validation Engines, Role-based Data Isolation
References

START_HERE.md - Entry point Phase 9.1 Frozen v2
AGENTS.md - Zero Domain Knowledge, Single source of truth
CHANGELOG.md [9.1.0] - 2026-09-05
docs/IMPORT_MAP_FROZEN_V2.md - 0 violations frozen
