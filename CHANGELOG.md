CHANGELOG.md — AI Website Framework
All notable changes to this project are documented in this file.

[9.1.0] - 2026-09-05 — Frozen v2 — Legacy Removal Complete
Status: GREEN [100%] — Canonical Only

This release completes Phase 9 cleanup per AGENTS.md Zero Domain Knowledge principle. Legacy generation framework/ is fully removed.

Removed
framework/ — entire legacy directory deleted (old generation with core/, contracts, exceptions, slug)
11 legacy test files that depended on framework/:
test_framework_*
test_ai_website_generator*
test_image_processor*
test_political_bias*
test_website_templates
plugins/telegram/ — last legacy tail
File: plugins/telegram/publisher.py
Reason: from framework.core.contracts import PublisherPluginContract and from framework.core.exceptions
Old interface: get_metadata(), validate(), publish() with direct requests usage
Action: Remove-Item -Recurse -Force plugins/telegram — now plugins/ is empty (intentional)
Dump artifacts created during Phase 9 analysis:
TREE_FROZEN.txt, DUMP_FROZEN.txt, IMPORT_MAP.txt
framework_inventory_before.txt, framework_inventory_after.txt
git_status_before.txt, pytest_after_framework_delete.txt, remaining_framework_imports.txt
*_before, *_after temporary files
Fixed
ai_framework/application/pipeline/slug_orchestrator.py
Before: from framework.core.slug import SlugGenerator (broken, with encoding ÐŸÐ»Ð°Ð³Ð¸Ð½)
After: from ai_framework.services.slug import SlugGenerator, DefaultCollisionResolver
Canonical import per ai_framework/plugins/contracts.py and ai_framework/services/slug.py
Verified
Residual check:
powershell

Get-ChildItem -Recurse -File -Include *.py | Select-String -Pattern "from\s+framework(\s|.)|import\s+framework(\s|.)" | Where-Object { $_.Line -notmatch "ai_framework" }

→ 0 results — no legacy imports remain
- **Plugin check:**
```powershell
dir plugins              # → empty
dir plugins\telegram     # → not found
Regression:
powershell

python -m pytest -q

→ ........................................................................
→ [100%] GREEN
Expected ~392 passed (telegram added no tests, count same as after Step 3)
Actual count from final run: see pytest_final.txt or pytest output tail
- **Structure after cleanup:**
ai_framework/
docs/
plugins/ (empty placeholder)
showcases/
tests/
pyproject.toml, pytest.ini, .gitignore
AGENTS.md, README.md, CHANGELOG.md, START_HERE.md, CHAT_BOOTSTRAP.md


### Migration Notes
- Any code importing `from framework.*` or `import framework` must migrate to `from ai_framework.*`
- `ai_framework/plugins/contracts.py` is the new contract for publisher plugins
- `ai_framework/services/slug.py` provides `SlugGenerator` and `DefaultCollisionResolver`
- `plugins/` directory is for external plugins only and must not depend on legacy `framework`

### Next Steps
- Use `ai-website-framework -copi-git` as main project (this frozen v2)
- Delete old folder `ai-website-framework` containing `framework/`
- Commit and push:
```powershell
git add -A
git commit -m "phase-9-frozen-v2: remove legacy framework/ + 11 tests + plugins/telegram, fix slug_orchestrator canonical import, pytest GREEN 100%"
git push
[9.0.0] - 2026-09-05 — Phase 9 Frozen — Initial Legacy Framework Removal
Removed
Identified legacy framework/ as deletable per AGENTS.md
Added
Phase 9 cleanup plan: inventory, collection error analysis, test removal strategy
Fixed
Initial attempt to fix slug_orchestrator.py encoding
[8.x] — Previous Phases
Added
ai_framework/ canonical implementation
Pipeline: UseCases → Pipeline → CRUD → AssetManager → Publisher
AI Provider adapters, API adapter, Domain value objects
Services: slug, etc.
Changed
Migration from old framework/ to new ai_framework/ started
Guidelines for Future Changes
Keep framework/ deleted — do not reintroduce
All new code must import from ai_framework.*
Maintain pytest -q GREEN [100%]
Update START_HERE.md on each phase freeze
No dump files (*_FROZEN*, *_inventory_*) in repo root
Generated: 2026-09-05 — Phase 9.1 Frozen v2

