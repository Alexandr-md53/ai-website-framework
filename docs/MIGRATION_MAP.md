# Migration Map: Reference Project Extraction & Generalization Roadmap

**Document Version:** 4.0 (Phase 9 — FROZEN)
**Last Reviewed:** 2026-08-26
**Status:** COMPLETED / FROZEN — 444 / 444 GREEN
**Frozen Tag:** `phase-9-frozen-v2`
**Reference Status:** True Reference — replaces invalid `8dd0002e`

---

## 1. Migration Philosophy & Rules

The Plant Nursery (`site_generation_post`) is the **Reference Implementation**, not the Framework itself.

The extraction pipeline follows this strict flow:

```text
Reference Project Requirements
        ↓
Generalization
        ↓
Framework Specification
        ↓
TDD
        ↓
ai_framework
```

### Key Rules

1. **Canonical Package:** `ai_framework` is the only canonical Core package. The legacy `framework/` package is removed.
2. **Zero Domain Knowledge:** Core contains no references to plants, nurseries, cafe, lawyer, or other client-specific domain concepts.
3. **Canonical Imports:** Framework code uses `from ai_framework.*` only. Imports from `framework.*` are forbidden.
4. **Single Source of Truth:** Every universal framework capability exists in exactly one canonical location.
5. **Reference Project Isolation:** Code existing in the Reference Project does not automatically qualify as framework code. Reusable capabilities must be generalized, specified, implemented, and tested independently.

---

## 2. Final Framework Baseline — Phase 9 COMPLETED

### Block A — Foundation

| Module            | Canonical Location          | Status |
| ----------------- | --------------------------- | ------ |
| Validation Engine | `ai_framework/validation/`  | ✅ DONE |
| CRUD Engine       | `ai_framework/crud/`        | ✅ DONE |
| AI Provider       | `ai_framework/ai_provider/` | ✅ DONE |
| AI Pipeline       | `ai_framework/pipeline/`    | ✅ DONE |

**Recorded Block A baseline:** 241 tests passed.

### Phase 5 — Universal Services

| Module            | Canonical Location                                           | Status                                                                 |
| ----------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------- |
| Slug Service      | `ai_framework/services/slug/`                                | ✅ DONE — transliteration, URL-safe normalization, collision resolution |
| Localization      | `ai_framework/localization/`                                 | ✅ DONE                                                                 |
| Persistence Layer | `ai_framework/crud/persistence.py` + `sqlite_persistence.py` | ✅ DONE                                                                 |
| Asset Manager     | `ai_framework/asset_manager/`                                | ✅ DONE                                                                 |

### Phase 6–7 — Metadata, CRUD UI & Admin Platform

| Module           | Canonical Location       | Status |
| ---------------- | ------------------------ | ------ |
| Metadata Engine  | `ai_framework/metadata/` | ✅ DONE |
| CRUD UI Engine   | `ai_framework/crud_ui/`  | ✅ DONE |
| Settings Manager | `ai_framework/settings/` | ✅ DONE |
| API Layer        | `ai_framework/api/`      | ✅ DONE |

### Phase 8 — Security

| Module                   | Canonical Location                       | Status |
| ------------------------ | ---------------------------------------- | ------ |
| Security Domain          | `ai_framework/security/`                 | ✅ DONE |
| Authentication / RBAC    | `ai_framework/security/authorization.py` | ✅ DONE |
| Web Security Integration | `ai_framework/security/web.py`           | ✅ DONE |

### Phase 9 — Business Showcases

Phase 9 validates framework universality through three independent business domains without introducing domain-specific knowledge into Core.

| Showcase      | Domain         | Key Features                                             | Status |
| ------------- | -------------- | -------------------------------------------------------- | ------ |
| Plant Nursery | Plant nursery  | Hierarchy, media, inventory, pricing                     | ✅ DONE |
| Cafe          | Cafe           | Dynamic UI, status lifecycle, menu, modifiers, RBAC      | ✅ DONE |
| Lawyer        | Legal services | M2M graphs, complex validation, consultations, isolation | ✅ DONE |

**Recorded Phase 9 baseline:**

```text
407 core tests + 37 showcase tests = 444 / 444 GREEN
```

**Quality Gate:** 7-Point Quality Gate PASSED for all completed modules.

> The `444 / 444` figure above is the recorded pre-cleanup Phase 9 baseline. The final clean-project test count must be confirmed by the post-cleanup regression run and must not be assumed in advance.

---

## 3. Packaging Boundary — FROZEN

The canonical framework package is:

```text
ai_framework/
```

The distribution package is:

```text
ai-website-framework
```

The legacy package:

```text
framework/
```

is **REMOVED** from the clean Phase-9 Frozen Reference.

The legacy `framework/` tree present in commit `8dd0002e` is classified as an **INVALID FROZEN ARTIFACT** and must not exist in the clean reference.

### `pyproject.toml`

Canonical package discovery:

```toml
[tool.setuptools.packages.find]
where = ["."]
include = ["ai_framework*"]
```

No `framework.*` package is part of the canonical distribution.

---

## 4. Phase 9 Freeze Boundary

Phase 9 is the final validated business-showcase phase.

The Frozen Reference must satisfy all of the following:

* `ai_framework/` is the only canonical framework package.
* `framework/` does not exist.
* No production code imports `framework.*`.
* No canonical tests depend on `framework.*`.
* Documentation contains no AI-generation dialogue or conversational artifacts.
* Dump/audit helper files are not part of the product unless explicitly required.
* Packaging exposes `ai_framework*` only.
* Plant Nursery, Cafe, and Lawyer showcases remain outside Core domain logic.
* Full regression is GREEN after cleanup.
* The resulting Git working tree is clean before the final freeze.

---

## 5. Next Steps After Phase 9

Phase 9 is **feature-complete for the validated business showcase baseline**.

Phase 10 contains post-freeze hardening and API refinement tasks rather than additional migration of the Reference Project.

Current accepted tasks:

* **TASK-10G.1R:** `CRUDEngine` Facade over `UniversalCRUDEngine` — accepted; clean implementation required in `ai_framework/crud/crud_engine.py`.
* **TASK-10H:** Positional mapping safety — accepted.
* **TASK-10I.1:** Patch only `crud_engine.py` — pending; designated next task.

These tasks do not reopen the Phase 9 migration baseline.

---

## 6. Invalid Frozen v1 — Historical Record

The previous frozen commit:

```text
8dd0002e448efab4a4abfdaf7b3efe372c46580f
```

is **NOT** considered a valid Frozen Reference.

The commit is retained only as a historical record.

Known invalid artifacts in that snapshot included:

1. `START_HERE.md` containing AI-generation dialogue.
2. `AGENTS.md` containing AI-generation dialogue.
3. `docs/MIGRATION_MAP.md` containing AI-generation dialogue instead of a clean canonical document.
4. The legacy `framework/` directory remaining in the repository.
5. `pytest.ini` containing a duplicated `[pytest]` configuration header.
6. Documentation containing stale Phase 5 / Phase 6 roadmap information inconsistent with the Phase 9 completion state.

These issues are corrected in the `phase-9-frozen-v2` cleanup.

---

## 7. Frozen Reference Definition

The valid Phase-9 Frozen Reference is defined as:

```text
phase-9-frozen-v2
```

It replaces the invalid frozen snapshot:

```text
8dd0002e
```

The Frozen Reference represents the **clean architectural baseline after Phase 9**, not merely a copy of the historical repository state.

The following hierarchy applies:

```text
Knowledge Core / Canonical Specifications
                ↓
       Architectural Contract
                ↓
        Clean Project on Disk
                ↓
          Test Evidence
                ↓
       phase-9-frozen-v2
```

`CODEBASE_DUMP_FOR_GEMINI.md` and similar generated dumps are analysis snapshots only. They are not Source of Truth and are not part of the architectural contract.

---

## 8. Final Status

```text
PHASE 9

Foundation              ✅
Universal Services      ✅
Metadata / CRUD UI      ✅
Settings / API          ✅
Security                ✅
Business Showcases      ✅
Architecture Cleanup    ⏳
Final Clean Regression  ⏳
Frozen Reference v2     ⏳
```

After the cleanup pass and final regression have been completed:

```text
PHASE 9 — FROZEN

Canonical package       ai_framework
Legacy framework/       REMOVED
Legacy imports          0
Documentation           CLEAN
Packaging boundary      CLEAN
Showcases               VALIDATED
Regression              GREEN
Git working tree        CLEAN
Frozen tag              phase-9-frozen-v2
```

**Final Freeze Condition:** `phase-9-frozen-v2` may be created only after the clean project passes its final regression suite and all architectural cleanup requirements are verified.
