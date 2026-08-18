Обновлённая каноническая версия файла docs/framework-architecture.md (v1.2) с учётом всех уточнений по Zero Domain Knowledge, __slug_config__ и фасадной оркестрации:

Markdown
# High-Level Runtime Architecture

**Document:** `framework-architecture.md`  
**Status:** Approved (v1.2)  
**Version:** 1.2  

The Framework consists of operational runtime engines and orchestration layers that handle data flow, persistence, slug management, and AI content generation as independent, decoupled subsystems.

```text
                     Application / Domain Layer
                                 │
                     ┌───────────┴───────────┐
                     │                       │
                     ▼                       ▼
               CRUD Subsystem          AI Pipeline Subsystem
                     │                       │
           ┌───────────────────┐   ┌───────────────────┐
           │ CRUDEngine Facade │   │ AIService Orch.   │
           └─────────┬─────────┘   └─────────┬─────────┘
     ┌───────────────┼───────────────┐       │
     ▼               ▼               ▼       ▼
Validation      UniversalCRUD     AsyncSlug AI Provider
  Engine        (Low-Level)     Orchestrator Subsystem
                     │
                     ▼
            PersistenceProvider
             (In-Memory/SQLite)
1. Core Framework Subsystems
1.1 CRUD & Persistence Subsystem (ai_framework.crud)
CRUDEngine (Facade Layer): High-level schema-aware facade layer separating low-level storage operations from domain-level schema logic (__slug_config__). Orchestrates data validation via ValidationEngine, persistence via UniversalCRUDEngine, and slug lifecycle resolution via AsyncSlugOrchestrator.

ValidationEngine: Execution boundary for schema validation. Enforces data integrity prior to state mutations (Validation-First principle).

UniversalCRUDEngine (Low-Level CRUD): Pure storage abstraction providing universal CRUD operations across backend persistence providers without domain or slug awareness.

AsyncSlugOrchestrator (Slug Service): Asynchronous slug manager handling custom slug validation, auto-generation from mapped source fields defined in __slug_config__, and iterative collision resolution (-2, -3).

PersistenceProvider: Storage backend contract and implementation (In-Memory, SQLite, Relational DBs).

1.2 AI Pipeline Subsystem (ai_framework.ai)
Prompt Pipeline: Assembles structured prompt components, system instructions, and dynamic context parameters.

AIService (Orchestrator): Manages AI execution lifecycle, provider routing, fallback policies, and retry strategies.

StructuredOutputParser: Validates and converts LLM output into strictly structured JSON or schema contracts.

AI Provider Subsystem: Low-level provider protocol abstraction (OpenRouter protocol, caching, resilience, rate-limiting).

2. Architectural Rules & Subsystem Isolation
Decoupled Subsystems: The CRUD Subsystem and AI Pipeline Subsystem operate as independent architectural branches. Basic CRUD operations do not implicitly invoke AI services. Orchestration between storage and AI generation occurs exclusively at the Application / Domain Layer.

Validation-First: Mutation requests are validated before persistence mutations are performed. Slug resolution and uniqueness checks are orchestrated by CRUDEngine through AsyncSlugOrchestrator.

Zero Domain Knowledge: CRUDEngine operates strictly on structural metadata contracts (__slug_config__, using keys such as source_field and slug_field) without awareness of domain entities (such as plants, articles, products, or doctors) or business semantics.

Standalone Storage Reliability: The CRUD and persistence layer remains 100% operational without any dependency on external AI services.