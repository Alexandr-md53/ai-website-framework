# AI Website Framework — Project Roadmap

Phase 1–4: Initial Framework Core & Generator (Завершено ✅)
[x] Phase 1: Core Foundation
[x] Phase 2: Modular Engines & Provider Layers
[x] Phase 3: Generator Pipeline
[x] Phase 4: Quality & Testing

# Phase 5: Reference Project Analysis & Core Infrastructure (Завершено ✅)
[x] 5.1 Reference Project Analysis (REFERENCE_PROJECT_ANALYSIS.md)
[x] 5.2 Migration Map Creation (MIGRATION_MAP.md)
[x] 5.3 Core Infrastructure Modules & Engines
  [x] 5.3.1 Localization Engine (LOC_01) — Completed
  [x] 5.3.2 Slug Service (SLG_01) — Completed
  [x] 5.3.3 Asset Manager (ASM_01) — Completed
  [x] 5.3.4 Persistence Layer (DB_01) — Completed
  [x] 5.3.5 Validation Engine (VL_01) — Completed
  [x] 5.3.6 CRUD Engine & Slug Integration (CRUD_SLG_01) — Completed (commit dd543f7)

# Phase 6: Application & Domain Layer (Завершено ✅) ✅ COMPLETE / FROZEN

- [x] **6.1 Domain Layer** 🟢 (Entities, Value Objects, Domain Events, Repository Contracts)
- [x] **6.2 Application Layer** 🟢 (Use Cases, DTOs, Unit Tests)
- [x] **6.3 Infrastructure Adapters** 🟢 (CRUDArticleRepository -> UniversalCRUDEngine -> PersistenceProvider)
- [x] **6.4 Application Pipeline** 🟢 NEXT (Request/Response Pipeline contract & execution flow)
 - [x] End-to-end Request → Application Service → CRUDEngine → Event → Response

# Phase 7: Universal Admin Panel Engine (Завершено ✅) ✅ FROZEN (f0a067a)
[x] 7.1 Metadata Engine & Driven Forms  ✅ FROZEN
[x] 7.2 Dynamic Content-Type CRUD UI    ✅ FROZEN (включая Web Integration Layer)
[x] 7.3 Universal Media & Settings Manager ✅ COMPLETE / FROZEN
[x] 7.3.1 Media UI Bridge              ✅ COMPLETE / FROZEN (46/46 GREEN)
[x] 7.3.2 Universal Settings Manager   ✅ COMPLETE / FROZEN

## Phase 8: Security Domain & Integration [COMPLETED] ✅ FROZEN
- [x] Stage 8.1: Core Security Domain Models (Permission, Role, Identity, SecurityContext)
- [x] Stage 8.2: Authentication Engine & Credentials Providers
- [x] Stage 8.3: RBAC & Authorization Engine (RoleBasedAuthorizationProvider, AuthorizationService)
- [x] Stage 8.4: Web & Admin UI Security Integration (SecurityWebGuard, BearerTokenExtractor, SecuredViewModelAdapter)



## [x] Phase 9 — Business Showcases (✅ COMPLETED / FROZEN)

**Цель:** Подтверждение универсальности `ai_framework` на трех независимых бизнес-доменах без загрязнения ядра доменной логикой.

- [x] **Phase 9.1 — Plant Nursery Showcase** (16 tests GREEN)
  - Иерархические категории товаров
  - Галерея медиа-контента
  - Управление остатками (Inventory) и критерии поиска
- [x] **Phase 9.2 — Cafe Showcase** (12 tests GREEN)
  - Спецификация канонических Dynamic Forms / Admin UI (Phase 7)
  - Жизненный цикл статусов (`DRAFT` → `ACTIVE` → `ARCHIVED`)
  - Динамические модификаторы цены
  - Ролевой доступ (RBAC: Barista / Manager)
- [x] **Phase 9.3 — Lawyer / Service Showcase** (9 tests GREEN)
  - Граф связей M2M (`Attorney ↔ PracticeArea ↔ Service`)
  - Сложная бизнес-валидация заявок (`ConsultationRequestValidator`)
  - Изоляция данных по ролям (`ATTORNEY` vs `MANAGING_PARTNER`)

**Итоги Phase 9:**
- Всего тестов витрин: **37 / 37 GREEN**
- Регрессия проекта: **444 / 444 GREEN** (0 failures, 100% pass)
- Архитектурная гипотеза подтверждена: `ai_framework` полностью изолирован от `showcases`.