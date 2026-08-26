# Changelog

All notable changes to AI Website Framework are documented in this file.

The project follows semantic versioning.

---

## [Phase 9] — Business Showcases (2026-08-26)

### Added
- **Plant Nursery Showcase (16 tests GREEN)**: Иерархические категории товаров, галерея медиа-контента, управление остатками (Inventory) и критерии поиска.
- **Cafe Showcase (12 tests GREEN)**: Спецификация канонических Dynamic Forms / Admin UI, жизненный цикл статусов (`DRAFT` → `ACTIVE` → `ARCHIVED`), динамические модификаторы цены, RBAC.
- **Lawyer Showcase (9 tests GREEN)**: M2M-граф связей (`Attorney ↔ PracticeArea ↔ Service`), сложная бизнес-валидация заявок (`ConsultationRequestValidator`), ролевая изоляция данных (`ATTORNEY` vs `MANAGING_PARTNER`).

### Verified & Quality
- **Архитектурное доказательство**: Доказана универсальность `ai_framework` поверх 3 кардинально разных бизнес-доменов без загрязнения ядра доменным кодом.
- **Полная изоляция**: Пакет `ai_framework` не имеет обратных импортов или зависимостей от `showcases`.
- **100% Регрессия**: **444 / 444 тестов GREEN** (407 тестов ядра + 37 тестов витрин).

---

## [Phase 8] — Security & Access Control (2026-08-25)

### Added
- Доменные сущности безопасности: `Permission`, `Role`, `Identity`, `SecurityContext`.
- Расширяемый `AuthenticationService` с поддержкой `UsernamePasswordCredentials`, `TokenCredentials` и `InMemoryAuthenticationProvider`.
- Мелкозернистая RBAC-авторизация через `RoleBasedAuthorizationProvider` по принципу Default Deny.
- `AuthorizationService` с поддержкой короткого замыкания (short-circuiting OR-evaluation) для составных провайдеров.
- Веб-интеграция (`SecurityWebGuard`, `BearerTokenExtractor`) для маппинга HTTP-заголовков в `SecurityContext` с защитой 401/403.
- `SecuredViewModelAdapter` для безопасной фильтрации действий в слое presentation без мутации данных.

---

## [Phase 7] — Settings Manager & Media UI Bridge (2026-08-24)

### Added
- **Universal Settings Manager (`ai_framework.settings`)**:
  - `SettingsProviderProtocol`: контракт хранилища настроек (`get`, `set`, `delete`, `get_all`, `has`).
  - `InMemorySettingsProvider`: in-memory реализация провайдера настроек.
  - `SettingsManager`: оркестратор настроек с поддержкой `namespace`, `defaults` и сброса к значениям по умолчанию.
  - `SettingsUIBridge`: адаптер для генерации UI-форм из настроек с авто-маппингом типов и обработкой submit.
- **Media UI Bridge (`ai_framework.crud_ui.media_bridge`)**:
  - `MediaUIBridge`: адаптер связи `FieldWidgetType.FILE` с `AssetManagerProtocol` для загрузки и разрешения ассетов.

### Changed
- Модуль `web.py` (`HTTPRequestContext`, `CrudWebController`, `WebResponseAdapter`) зафиксирован как опорный интеграционный слой в рамках Phase 7.2 (Dynamic CRUD UI).

---

## v1.1.0 — CRUD Engine & Slug Integration

### Added
- **`CRUDEngine` Facade**: Высокоуровневый слой оркестрации персистенции и резолюции слагов.
- **`UniversalCRUDEngine`**: Низкоуровневый слой CRUD-персистенции.
- **`SlugGenerator` & `AsyncSlugOrchestrator`**: Асинхронная генерация слагов и разрешение коллизий.
- **Explicit Collision Contracts**:
  - Ручные коллизии строго вызывают `ValueError`.
  - Авто-сгенерированные коллизии разрешаются суффиксами (`slug-2`, `slug-3`).

---

## v1.0.0 — Validation Engine

### Added
- `ValidationEngine`, `ValidationContext`, `ValidationResult`, `ValidationError`.
- Встроенный набор валидаторов и компилятор схем.
- Поддержка Dependency Injection.
- Публичный API (`validate()`, `validate_entity()`).

### Quality
- 121 автоматический тест, 100% покрытие встроенных валидаторов.

---

## v0.1.0 — Core Foundation

### Added
- Базовая структура пакета `ai_framework`.
- Базовые модули: `Exceptions`, `Contracts`, `Registry`, `Settings`, `Component Loader`, `Version`.
- Инициализировано 26 базовых тестов ядра.