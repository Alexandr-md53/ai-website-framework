# Changelog

All notable changes to AI Website Framework are documented in this file.

The project follows semantic versioning.

# Changelog

All notable changes to AI Website Framework are documented in this file.

The project follows semantic versioning.

---

## v1.1.0 — CRUD Engine & Slug Integration (commit dd543f7)

### Added
- **`CRUDEngine` Facade**: High-level schema-aware facade layer orchestrating persistence and slug resolution.
- **`UniversalCRUDEngine`**: Low-level storage and CRUD persistence layer.
- **`SlugGenerator` & `AsyncSlugOrchestrator`**: Asynchronous slug generation, validation, and collision resolution.
- **Explicit Collision Contracts**:
  - Explicit custom slug collisions strictly raise `ValueError`.
  - Auto-generated slug collisions resolve via iterative numerical suffixes (`slug-2`, `slug-3`).

### Quality
- 100% PASS on full pytest regression suite (including integration tests for `CRUDEngine` + `AsyncSlugOrchestrator`).
- Clean working tree locked at commit `dd543f7`.

---

## v1.0.0 — Validation Engine
...
---

# Version 0.1.0 — Core Foundation

Release status:

```text
Foundation Release
```

## Overview

The first architectural milestone of AI Website Framework.

This release establishes the Framework Core and provides the fundamental infrastructure required for future Framework components.

## Added

### Core Architecture

- Core package structure
- Framework documentation
- Dependency rules
- Module responsibility definitions

### Core Modules

- Exceptions
- Contracts
- Registry
- Settings
- Component Loader
- Version

### Testing

Implemented automated tests for:

- Registry
- Contracts
- Settings
- Loader
- Version

Result:

```text
26 tests passing
```

## Notes

This release intentionally does not include business logic.

Its purpose is to establish a stable and extensible foundation for all future Framework modules.

Future releases will build on this Core without changing its architectural principles.

## v1.0.0 — Validation Engine

### Added

- ValidationEngine
- ValidationContext
- ValidationResult
- ValidationError
- Built-in validators
- Schema compiler
- Dependency Injection
- validate()
- validate_entity()

### Quality

- 121 automated tests
- Public API fully tested
- Built-in validators fully covered
- Integration tests completed
- Production Ready

## [Unreleased] — 2026-08-24

### Added
- **Universal Settings Manager (`ai_framework.settings`)**:
  - `SettingsProviderProtocol`: абстрактный контракт хранилища настроек (`get`, `set`, `delete`, `get_all`, `has`).
  - `InMemorySettingsProvider`: базовая in-memory реализация провайдера настроек.
  - `SettingsManager`: оркестратор настроек с поддержкой пространств имён (`namespace`), дефолтных значений (`defaults`), агрегированного `list()` и сброса к значениям по умолчанию (`reset()`).
  - `SettingsUIBridge`: адаптер для генерации UI-форм из настроек (`FormViewModel`) с авто-маппингом типов (`bool` → `checkbox`, `int`/`float` → `number`, `str` → `text`) и безопасным сохранением POST-данных (`handle_submit`).
- **Media UI Bridge (`ai_framework.crud_ui.media_bridge`)**:
  - `MediaUIBridge`: адаптер связи `FieldWidgetType.FILE` с `AssetManagerProtocol` для обработки загрузок (`handle_upload`), разрешения и презентации ассетов (`resolve_asset`, `present_asset`).

### Changed / Architectural Alignment
- **Web Integration Layer**:
  - Модуль `web.py` (`HTTPRequestContext`, `CrudWebController`, `WebResponseAdapter`) официально зафиксирован как опорный интеграционный слой в рамках **Phase 7.2 (Dynamic CRUD UI)** без выделения в отдельную фазу `7.4`.
  - Документация и тестовое покрытие актуализированы под канонический вид `ROADMAP.md`.

### Testing & Regression
- Покрыты unit- и интеграционными тестами модули `tests/settings/` (`test_settings_provider`, `test_settings_manager`, `test_settings_ui_bridge`).
- Достигнут **100% GREEN** регрессионный прогон по пакетам `tests/settings` и `tests/crud_ui`.

## [Phase 8] - 2026-08-25

### Added
- Core Security domain entities: `Permission`, `Role`, `Identity`, `SecurityContext`.
- Extensible `AuthenticationService` supporting `UsernamePasswordCredentials`, `TokenCredentials`, and `InMemoryAuthenticationProvider`.
- Fine-grained RBAC authorization via `RoleBasedAuthorizationProvider` with Default Deny semantics.
- `AuthorizationService` supporting short-circuiting OR-evaluation across composite providers.
- Web integration layer (`SecurityWebGuard`, `BearerTokenExtractor`) mapping HTTP headers to `SecurityContext` with HTTP 401/403 protection.
- `SecuredViewModelAdapter` for non-mutating presentation-layer action filtering based on context permissions.