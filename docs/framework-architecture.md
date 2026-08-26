# High-Level Runtime Architecture

**Document:** `framework-architecture.md`  
**Status:** Approved (v1.3 — Phase 9 Frozen)  
**Version:** 1.3  

The Framework consists of operational runtime engines, security boundaries, and presentation orchestration layers that handle data flow, persistence, slug management, access control, dynamic settings, and AI generation as independent, decoupled subsystems.

```text
                           Domain Showcases Layer (`showcases/`)
                   (Plant Nursery  |  Cafe  |  Lawyer Showcase)
                                      │
                   ┌──────────────────┴──────────────────┐
                   ▼                                     ▼
        Web / Presentation Layer               Application / Domain Layer
      (CrudWebController, Guards)                        │
                   │                                     │
    ┌──────────────┼───────────────────────┬─────────────┴─────────────┐
    ▼              ▼                       ▼                           ▼
Security      Settings & UI             CRUD Subsystem           AI Pipeline Subsystem
Subsystem       Subsystem                  │                           │
(RBAC/Guard) (SettingsManager/Bridges)  ┌──┴────────────────┐      ┌───┴───────────────┐
                                        │ CRUDEngine Facade │      │ AIService Orch.   │
                                        └────────┬──────────┘      └───┬───────────────┘
                                 ┌───────────────┼───────────────┐     │
                                 ▼               ▼               ▼     ▼
                            Validation      UniversalCRUD     AsyncSlug AI Provider
                              Engine         (Low-Level)    Orchestrator Subsystem
                                                 │
                                                 ▼
                                        PersistenceProvider
                                         (In-Memory/SQLite)

                                         1. Core Framework Subsystems (ai_framework)
1.1 CRUD & Persistence Subsystem (ai_framework.crud)
CRUDEngine (Facade Layer): High-level schema-aware facade separating low-level storage operations from schema metadata (__slug_config__). Orchestrates data validation via ValidationEngine, persistence via UniversalCRUDEngine, and slug lifecycle via AsyncSlugOrchestrator.

ValidationEngine: Execution boundary for schema validation enforcing data integrity prior to state mutations (Validation-First principle).

UniversalCRUDEngine (Low-Level CRUD): Pure storage abstraction providing universal CRUD operations across backend persistence providers without domain or slug awareness.

AsyncSlugOrchestrator: Asynchronous slug manager handling custom slug validation, auto-generation from mapped source fields, and iterative collision resolution (-2, -3).

PersistenceProvider: Storage backend contract and implementation (InMemoryPersistenceProvider, SQLitePersistenceProvider).

1.2 Security & Access Control Subsystem (ai_framework.security)
Core Entities: Domain-agnostic primitives for security (Permission, Role, Identity, SecurityContext).

AuthenticationService: Extensible auth provider handling credentials (UsernamePasswordCredentials, TokenCredentials) and token resolution.

AuthorizationService: Fine-grained authorization runtime supporting RoleBasedAuthorizationProvider with Default Deny semantics and short-circuiting OR-evaluation across composite providers.

Web & Presentation Guards: SecurityWebGuard and BearerTokenExtractor mapping HTTP headers to SecurityContext with HTTP 401/403 protection; SecuredViewModelAdapter for non-mutating action filtering in presentation layers.

1.3 Settings & UI Bridge Subsystem (ai_framework.settings, ai_framework.crud_ui)
Settings Infrastructure: SettingsManager supporting namespacing, default fallbacks, and storage contracts (SettingsProviderProtocol).

SettingsUIBridge: Adapter translating settings schemas into dynamic form view models (FormViewModel) with automatic widget mapping and POST handling.

MediaUIBridge: Presentation-to-asset mapping connecting FieldWidgetType.FILE widgets to AssetManagerProtocol for secure asset upload, resolution, and presentation.

Web Integration Layer (ai_framework.web): HTTPRequestContext, CrudWebController, and WebResponseAdapter delivering standardized HTTP handling over framework components.

1.4 AI Pipeline Subsystem (ai_framework.ai)
Prompt Pipeline: Assembles structured prompt components, system instructions, and dynamic context parameters.

AIService (Orchestrator): Manages AI execution lifecycle, provider routing, fallback policies, and retry strategies.

StructuredOutputParser: Validates and converts LLM output into strictly structured JSON or schema contracts.

AI Provider Subsystem: Low-level provider protocol abstraction (OpenRouter protocol, caching, resilience, rate-limiting).

2. Architectural Rules & Subsystem Isolation
Zero Domain Knowledge: ai_framework operates strictly on structural contracts, interfaces, and metadata schemas (__slug_config__, generic RBAC roles, provider protocols) without imports or awareness of specific domain entities (plants, menu items, legal services).

Decoupled Subsystems: CRUD operations, Security enforcement, Settings management, and AI execution operate as independent branches. Basic CRUD does not implicitly invoke AI services or mandate specific Auth providers.

Validation-First & Security-First: All state mutations are validated via ValidationEngine and checked against SecurityContext prior to persistence operations.

Standalone Storage Reliability: The core framework and persistence layers remain 100% operational without dependency on external AI APIs or specific frontend components.

3. Infrastructure & Repository Pattern Integration
Chain of Responsibility
Plaintext
Domain Repository Interface (e.g., ArticleRepository)
        ▲
        │ (implements)
Infrastructure Repository (e.g., CRUDArticleRepository)
        │ (invokes async execution)
UniversalCRUDEngine (UniversalCRUDEngineProtocol)
        │ (delegates)
PersistenceProviderProtocol (InMemory / SQLite)
Engine Target: Infrastructure repositories interact with UniversalCRUDEngineProtocol for standard CRUD primitives (get, create, update, delete, list).

Engine Preservation: CRUDEngine remains a high-level orchestration facade and is not modified to fit individual domain repository implementations.

Adapter Boundary: Repositories serve as explicit boundaries between synchronous domain logic and asynchronous CRUD runtime.

4. Business Showcases Layer (showcases/)
The framework's universality and zero-leakage principle are proven by three isolated reference showcases built on top of ai_framework:

Plant Nursery Showcase: Validates multi-level category hierarchies, media asset resolution (MediaUIBridge), inventory tracking, and search metadata.

Cafe Showcase: Validates dynamic admin form generation (SettingsUIBridge), status lifecycles (DRAFT → ACTIVE → ARCHIVED), price modifiers, and menu item RBAC.

Lawyer Showcase: Validates Many-to-Many entity graphs (Attorney ↔ PracticeArea ↔ Service), complex multi-field validation engines, and role-based data isolation (ATTORNEY vs MANAGING_PARTNER).


---

### Ключевые изменения относительно v1.2

* Добавлен **раздел 1.2 (Security Subsystem)**: отражены RBAC, `SecurityContext`, `AuthorizationService` и веб-гарды.
* Добавлен **раздел 1.3 (Settings & UI Bridge Subsystem)**: зафиксированы `SettingsManager`, `SettingsUIBridge`, `MediaUIBridge` и `web.py`.
* Добавлен **раздел 4 (Business Showcases Layer)**: задокументированы результаты **Phase 9** и паттерны, вынесенные в `showcases/`.
* Обновлена **диаграмма архитектуры**: добавлена связка слоя витрин с веб-контроллерами, безопасностью и настройками.

<FollowUp label="Хотите зафиксировать этот файл в git и свериться с ROADMAP.md для следующе