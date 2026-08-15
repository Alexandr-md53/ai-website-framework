Да. Теперь, когда **MIGRATION_MAP v2.1 уже отражает реальное состояние проекта**, старый `START_HERE.md` действительно пора переписать.

Главная проблема старого файла — он описывает Framework как проект на стадии первоначального формирования. Сейчас у нас уже другая архитектурная реальность:

* `ai_framework` — каноническое ядро;
* Validation Engine завершён;
* Metadata, Pipeline, Registry, AI, Template, Localization, Slug, Asset, Persistence уже выделены;
* Stage 1 завершён;
* следующий большой шаг — **CRUD Engine**;
* Plant Nursery теперь официально Reference Implementation;
* `framework/` больше нельзя описывать как место расположения Core;
* появился строгий **7-Point Quality Gate**;
* появился Package Architecture / Single Source of Truth;
* PlantSchema — не Core, а application/domain layer.

Я бы **полностью заменил старый `START_HERE.md`**, а не пытался его дописывать.

Вот версия, которую предлагаю сделать канонической.

---

# START_HERE.md

````markdown
# START_HERE.md

# AI Website Framework

## Project Context, Architecture & Development Rules

**Status:** Active  
**Canonical Package:** `ai_framework`  
**Reference Implementation:** `site_generation_post` (Plant Nursery)

---

# 1. Purpose

This document is the entry point for every developer, AI assistant, or contributor working on the AI Website Framework.

Before modifying code, read this document together with:

- `README.md`
- `MIGRATION_MAP.md`
- `REFERENCE_PROJECT_ANALYSIS.md`
- `DEVELOPMENT_WORKFLOW_SOP.md`
- `PACKAGE_ARCHITECTURE.md`

These documents define the current architecture, development workflow,
migration strategy, and package boundaries.

---

# 2. Project Mission

AI Website Framework is a reusable architectural platform for building
business websites from universal components.

The Framework is designed to support multiple business domains:

- Plant Nursery
- Cafe
- Restaurant
- Hotel
- Medical Clinic
- Lawyer
- School
- Beauty Salon
- Portfolio
- etc.

The central principle is:

> Build universal capabilities once and reuse them across multiple domains.

The Framework must contain **zero domain-specific business logic**.

---

# 3. Two Connected Projects

Development is based on two separate repositories.

## 3.1 AI_Website_Framework

This is the Framework Core and the main reusable product.

Canonical Python package:

```text
ai_framework/
````

Only universal capabilities belong here.

Examples:

* Validation Engine
* Metadata Engine
* Generator Pipeline
* Plugin Registry
* AI Provider Layer
* Template Engine
* Localization Engine
* Slug Service
* Asset Manager
* Persistence Layer
* future CRUD Engine
* future Admin Platform

---

## 3.2 site_generation_post

This is the Reference Implementation.

It is the Plant Nursery project used to:

* analyze real business requirements;
* validate Framework architecture;
* provide behavioral reference implementations;
* perform integration/regression testing;
* identify reusable architectural capabilities.

The Reference Project is NOT part of the Framework Core.

Domain-specific functionality remains in the Reference Project.

Examples:

```text
Plant
PlantSchema
Plant Categories
Nursery-specific business rules
Plant-specific UI
Plant-specific presentation
```

---

# 4. Reference Implementation Principle

The Plant Nursery project follows this relationship:

```text
Reference Project
       │
       ▼
Reference Analysis
       │
       ▼
Extraction
       │
       ▼
Generalization
       │
       ▼
Framework Core
       │
       ▼
Reference Validation
```

The Reference Project validates the Framework.

The Framework must never be modified with Nursery-specific
exceptions or hacks merely to satisfy the Reference Project.

---

# 5. Canonical Package Architecture

The only canonical Framework package is:

```text
ai_framework/
```

The canonical location of the Validation Engine is:

```text
ai_framework/validation/
```

The same rule applies to all Framework Core modules.

Examples:

```text
ai_framework/
├── validation/
├── metadata/
├── generators/
├── plugins/
├── ai/
├── templates/
├── localization/
├── services/
└── db/
```

---

# 6. Single Source of Truth

Every universal Framework capability must have exactly one canonical
implementation.

### Rules

1. `ai_framework` is the only canonical Core package.
2. Framework modules must not be duplicated inside client projects.
3. Client projects must not contain copies of Core engines.
4. Validation logic belongs to `ai_framework.validation`.
5. Domain schemas belong to the application/project layer.
6. Framework imports must use `ai_framework`.
7. `sys.path` hacks are prohibited.
8. Framework projects must use standard Python package installation.
9. Duplicate implementations of the same Core capability are prohibited.

Canonical import example:

```python
from ai_framework.validation import ValidationEngine
```

Non-canonical imports such as:

```python
from framework.validation import ValidationEngine
```

must not be introduced into client code.

See:

`PACKAGE_ARCHITECTURE.md`

for detailed package and import rules.

---

# 7. Domain Separation

The Framework must not know anything about a specific business domain.

## Domain-specific examples

These belong to the project:

* Plant
* PlantSchema
* Nursery
* Watering
* Flowering
* Plant-specific categories
* Plant-specific business rules
* Plant-specific templates

## Universal examples

These belong to the Framework:

* Validation Engine
* Metadata Engine
* CRUD Engine
* Plugin Registry
* Persistence Layer
* Localization Engine
* Asset Manager
* Slug Service
* Generator Pipeline
* AI Provider abstraction

---

# 8. Current Framework Foundation

The following Core capabilities are currently implemented:

| Module              | Canonical Location                       | Status     |
| ------------------- | ---------------------------------------- | ---------- |
| Validation Engine   | `ai_framework/validation/`               | ✅ Complete |
| Metadata Engine     | `ai_framework/metadata/`                 | ✅ Complete |
| Generator Pipeline  | `ai_framework/generators/`               | ✅ Complete |
| Plugin Registry     | `ai_framework/plugins/`                  | ✅ Complete |
| AI Provider Layer   | `ai_framework/ai/`                       | ✅ Complete |
| Template Engine     | `ai_framework/templates/`                | ✅ Complete |
| Localization Engine | `ai_framework/localization/`             | ✅ Complete |
| Slug Service        | `ai_framework/services/slug.py`          | ✅ Complete |
| Asset Manager       | `ai_framework/services/asset_manager.py` | ✅ Complete |
| Persistence Layer   | `ai_framework/db/`                       | ✅ Complete |

---

# 9. Current Migration Status

## Stage 1 — Basic Universal Services

Status:

```text
✅ COMPLETED
```

Completed:

* Localization Engine
* Slug Service
* Asset Manager

---

## Validation Engine

Status:

```text
✅ COMPLETED
```

The Validation Engine is part of the Framework Core.

Canonical location:

```text
ai_framework/validation/
```

The Reference Project has successfully validated integration through
`PlantSchema`.

The Reference Project keeps the application-level adapter:

```text
PlantSchema
```

The Framework provides:

```text
ValidationEngine
ValidationContext
ValidationResult
Validators
Contracts
```

This separation must be preserved.

---

# 10. Current Development Stage

The next major extraction target is:

```text
CRUD Engine
```

Target location:

```text
ai_framework/core/crud.py
```

The CRUD Engine must operate on top of:

```text
Metadata Engine
        +
Validation Engine
        +
Persistence Layer
```

Before implementation:

```text
CRUD_ENGINE_SPECIFICATION.md
```

must be created and approved.

See:

`MIGRATION_MAP.md`

for the complete migration roadmap.

---

# 11. Development Workflow

Every new Framework capability follows the standard lifecycle:

```text
Architecture
      ↓
Specification
      ↓
Reference Analysis
      ↓
Extraction
      ↓
Generalization
      ↓
Core Implementation
      ↓
Unit Testing
      ↓
Documentation
      ↓
NotebookLM Sync
      ↓
Reference Validation
      ↓
Status Update
      ↓
Quality Gate
```

The detailed procedure is defined in:

`DEVELOPMENT_WORKFLOW_SOP.md`

---

# 12. Extraction Rule

Before creating a new Core module, determine whether the required
behavior already exists in the Reference Project.

If it does:

1. Analyze the existing implementation.
2. Separate business logic from universal architecture.
3. Extract the reusable concept.
4. Generalize its interfaces.
5. Implement it in `ai_framework`.
6. Test it independently.
7. Validate it against the Reference Project.
8. Remove duplicate Core logic from the Reference Project.
9. Update migration documentation.

---

# 13. Metadata-First Principle

Universal platform capabilities should be driven by Metadata whenever
the architecture requires dynamic behavior.

The long-term platform direction is:

```text
Metadata
   ↓
Schema / Rules
   ↓
Validation
   ↓
CRUD
   ↓
Forms
   ↓
Admin UI
```

This principle is especially important for:

* CRUD Engine
* Dynamic Forms
* Admin Platform
* Entity Views
* Navigation
* Generators

---

# 14. 7-Point Quality Gate

A Framework module or migration phase is considered complete only when
all seven criteria are satisfied.

### 1. Zero Domain Knowledge

Core code contains no business-specific concepts.

### 2. Unit Tests

Executable business logic has test coverage of at least 90%.

### 3. Framework Specifications

Relevant specifications and technical documentation are synchronized.

### 4. NotebookLM Sync

Approved engineering knowledge has been synchronized with the
Permanent Knowledge Base.

### 5. Roadmap Sync

`MIGRATION_MAP.md` reflects the current status.

### 6. Migration Status Sync

`REFERENCE_PROJECT_ANALYSIS.md` reflects the current architecture.

### 7. Backward Compatibility

Reference Project and existing Framework tests remain green.

---

# 15. Documentation System

## README.md

High-level project description.

## START_HERE.md

Current project context, architecture, rules, and development entry point.

## CHANGELOG.md

Version history.

## ROADMAP.md

Strategic development roadmap.

## MIGRATION_MAP.md

Extraction and generalization roadmap from Reference Project to Framework.

## REFERENCE_PROJECT_ANALYSIS.md

Detailed architectural analysis of the Reference Implementation.

## DEVELOPMENT_WORKFLOW_SOP.md

Standard development lifecycle and Quality Gate.

## PACKAGE_ARCHITECTURE.md

Canonical package structure, import rules, and Single Source of Truth.

## docs/

Detailed technical specifications, architecture documents,
migration decisions, and implementation documentation.

---

# 16. NotebookLM

NotebookLM is the project's engineering knowledge base.

It is not a conversation archive.

Only approved and stable engineering knowledge should be synchronized.

Typical permanent knowledge includes:

* Framework architecture
* Package architecture
* Core module specifications
* Migration decisions
* Development SOP
* Quality Gate rules
* Reference Project analysis
* Stable architectural principles

Temporary debugging sessions, failed experiments, and ordinary
conversation history should not be treated as permanent architecture.

---

# 17. Working With the Reference Project

When implementing or migrating a feature, maintain a strict separation:

```text
AI_Website_Framework
        │
        │ universal architecture
        ▼
ai_framework
        ▲
        │ validation
        │
site_generation_post
        │
        │ domain implementation
        ▼
Plant / PlantSchema / Nursery Logic
```

The Reference Project may contain adapters that translate Framework
contracts into application-specific behavior.

These adapters are not automatically Framework code.

---

# 18. What Must NOT Be Done

Do not:

* duplicate Framework modules inside the Reference Project;
* create a second Validation Engine;
* create parallel `framework` and `ai_framework` Core implementations;
* import Core modules through non-canonical package names;
* add Nursery-specific logic to `ai_framework`;
* bypass Framework contracts with `sys.path` hacks;
* copy-paste Core code into a new business project;
* modify Core architecture solely to satisfy one domain-specific case.

When a new requirement appears, first determine whether it is:

```text
CORE
CORE SERVICE
PLUGIN
AI PROVIDER
ADMIN PLATFORM
PROJECT / DOMAIN
```

---

# 19. Current Strategic Direction

The Framework is moving from a collection of reusable components toward
a metadata-driven website platform.

Current priority:

```text
Foundation
   ↓
Validation
   ↓
Metadata
   ↓
CRUD
   ↓
Admin Platform
   ↓
Dynamic Forms
   ↓
Multi-Domain Website Generation
```

The next architectural milestone is the Universal CRUD Engine.

---

# 20. Core Philosophy

> Build once.
> Generalize correctly.
> Reuse everywhere.
> Keep the Core domain-free.
> Never duplicate solved problems.

The Reference Project demonstrates the architecture.

The Framework defines the architecture.

The Framework is the product.

---

# End of START_HERE.md

````

### Что здесь принципиально изменилось

Я бы обратил внимание на **четыре ключевых исправления**.

**1. Старое `framework/` больше не фигурирует как Core.**

Это важно после нашей истории с дублированием. Теперь в `START_HERE` прямо зафиксировано:

```text
ai_framework = единственный Core
````

**2. PlantSchema официально помещён на сторону приложения.**

Это очень важный результат сегодняшней миграции. Мы не переносим `PlantSchema` в Framework. Framework предоставляет механизм валидации, а `PlantSchema` адаптирует его под Plant.

**3. Validation Engine теперь не просто "в планах", а часть завершённого Foundation.**

Причём можно зафиксировать уже реальный результат:

```text
121 tests passed
```

и успешную интеграцию с Reference Project.

**4. Следующий шаг теперь однозначный: CRUD Engine.**

То есть после обновления `START_HERE` у AI, NotebookLM и любого нового чата будет одна и та же точка входа:

```text
Stage 1 — DONE
Validation — DONE
Foundation — DONE
             ↓
        CRUD Engine
             ↓
      Admin Platform
             ↓
      Dynamic Forms
```

И я бы **не добавлял сюда подробности Migration Decisions по PlantSchema**. Их правильнее оставить в отдельном документе вроде `docs/migration/PLANT_SCHEMA_MIGRATION.md` или в существующем журнале решений. `START_HERE` должен отвечать на вопрос **«где мы и какие правила действуют?»**, а не хранить историю отладки.

После этого `START_HERE.md` можно считать **новой канонической точкой входа**, а `MIGRATION_MAP.md` — документом, который отвечает уже на вопрос **«что делаем дальше?»**.
