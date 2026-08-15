Отличная корректировка! Эти исправления устраняют последние возможные смысловые двусмысленности:

1. **Принцип происхождения кода:** Чётко зафиксировано: наличие кода в Reference Project **не равно** его наличию во фреймворке.
2. **Гибкость порядка Phase 5:** Порядок `SLG → LOC → DB → ASM` объявлен как **`Proposed Execution Order`**, оставляя пространство для маневра по результатам dependency analysis.
3. **Легенда слоёв:** Таблица становится полностью самодокументируемой.

Ниже приведены финальные версии с учётом всех ваших правок.

---

## 📄 `MIGRATION_MAP.md` (v3.0 Final)

```markdown
# Migration Map: Reference Project Extraction & Generalization Roadmap

**Document Version:** 3.0 (Canonical Sync)  
**Last Reviewed:** 2026-08-14  
**Status:** Active Baseline  

---

## 1. Migration Philosophy & Rules

The Plant Nursery (`site_generation_post`) is the **Reference Implementation**, not the Framework itself.

The extraction pipeline follows a strict isolation flow:

$$\text{Reference Project Requirements} \longrightarrow \text{Generalization} \longrightarrow \text{Framework Specification} \longrightarrow \text{TDD} \longrightarrow \text{ai\_framework}$$

### Key Architectural Rules
1. **Canonical Package:** `ai_framework` is the only canonical Core package.
2. **Zero Domain Knowledge:** Core contains 0 references to plants, nurseries, or client domain concepts.
3. **Canonical Imports:** Client projects import Core exclusively through `ai_framework`.
4. **Single Source of Truth:** Every universal capability exists in exactly one canonical place.

---

## 2. Current Framework Baseline (Block A — Complete)

| Module | Canonical Location | Status | Test Baseline |
| :--- | :--- | :--- | :--- |
| **Validation Engine** | `ai_framework/validation/` | ✅ Implemented | Included in 241-test Block A baseline |
| **CRUD Engine** | `ai_framework/crud/` | ✅ Implemented | Included in 241-test Block A baseline |
| **AI Provider Subsystem** | `ai_framework/ai_provider/` | ✅ Implemented | Included in 241-test Block A baseline |
| **AI Pipeline Engine** | `ai_framework/pipeline/` | ✅ Implemented | Included in 241-test Block A baseline |

**Quality Gate:** **241 / 241 PASSED (0 failures, 0 warnings)**  
**Release Tag:** `1.0.0-stable`

---

## 3. Phase 5 Roadmap: Universal Services Migration

> **Core Principle:** Модули Phase 5 не считаются готовыми на основании наличия реализации в Reference Project. Они разрабатываются по стандартам TDD под каноничный `ai_framework`.

```text
Proposed Phase 5 Execution Order (subject to adjustment after dependency analysis):
┌──────────────────────────┐
│  SLG_01 — Slug Service   │  ◄── [PROPOSED TARGET 1: Minimal dependencies]
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ LOC_01 — Localization    │  ◄── [PROPOSED TARGET 2: Text/i18n abstraction]
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ DB_01 — Persistence Layer│  ◄── [PROPOSED TARGET 3: DB/ORM Abstraction]
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ ASM_01 — Asset Manager   │  ◄── [PROPOSED TARGET 4: Storage/Media Manager]
└──────────────────────────┘

```

### Module Specifications Status:

1. **`SLG_01` Slug Service** (`ai_framework/services/slug/` или `ai_framework/slug/`)
* *Status:* ⏳ **NEXT TASK (Proposed Target 1)**
* *Scope:* Transliteration, URL-safe normalization, collision handling, zero infrastructure dependencies.


2. **`LOC_01` Localization Engine** (`ai_framework/localization/`)
* *Status:* ⏳ **PLANNED (Phase 5)**
* *Scope:* Translation lookup, fallback mechanisms, locale management.


3. **`DB_01` Persistence Layer** (`ai_framework/db/`)
* *Status:* ⏳ **PLANNED (Phase 5)**
* *Scope:* DB abstraction, session lifecycle, repository primitives.


4. **`ASM_01` Asset Manager** (`ai_framework/services/asset/`)
* *Status:* ⏳ **PLANNED (Phase 5)**
* *Scope:* Storage abstraction, file lifecycle, image/PDF processing, metadata tracking.



---

## 4. Phase 6 Roadmap: Metadata & Admin Platform (Planned)

* **`MD_01` Metadata Engine** (`ai_framework/metadata/`) — Entity specs & form generation schema.
* **`ADM_01` Admin Platform** (`ai_framework/admin/`) — Dynamic Admin UI rendering.

---

## 5. 7-Point Quality Gate Standard

A Phase 5 module is marked as completed **ONLY** upon satisfying all 7 quality criteria:

* [ ] **1. Zero Domain Knowledge:** Core code contains 0 domain-specific terms.
* [ ] **2. Unit Tests Coverage:** Executable business logic test coverage $\ge 90\%$.
* [ ] **3. Framework Specs Sync:** Code documentation and module specs created/updated.
* [ ] **4. Architecture Alignment:** Strictly follows Dependency Inversion & Single Responsibility.
* [ ] **5. Roadmap Sync:** Status updated in `MIGRATION_MAP.md`.
* [ ] **6. Analysis Sync:** Status updated in `REFERENCE_PROJECT_ANALYSIS.md`.
* [ ] **7. Regression Passed:** All existing tests (241+) remain PASSED.

```

---

## 💡 Добавление легенды в `REFERENCE_PROJECT_ANALYSIS.md` (v4.0)

В раздел 3 файла `REFERENCE_PROJECT_ANALYSIS.md` добавляем следующую блок-инструкцию:

```markdown
### Легенда архитектурных слоёв:
* `[CORE]` — Implemented or target reusable Framework capability
* `[CORE SERVICES - TARGET]` — Target reusable service layer
* `[CORE / DB - TARGET]` — Target persistence abstraction
* `[PLANNED ADMIN]` — Future application/platform layer
* `[PROJECT]` — Reference Project domain

```

---

## 🏁 Итог: Documentation Audit Phase 5 официально закрыт!

Вся документация зафиксирована без единого противоречия:

```text
BLOCK A                   PHASE 5
Documentation   ✅       Documentation   ✅
Implementation  ✅       Implementation  ⏳ (Starting)
Tests (241/241) ✅       Next Target     → SLG_01

```

