Да, именно так и делаем.

Но есть технический момент: **сам репозиторий `AI_Website_Framework` сейчас не смонтирован в доступную мне файловую систему**, поэтому я не могу физически выполнить замену `docs/framework-architecture.md` или прочитать `framework-structure.md`. Попытка обратиться к PowerShell из среды выполнения также не сработала.

Чтобы не делать вид, что файл изменён, **я его сейчас не считаю изменённым**.

На твоей стороне выполни в PowerShell:

````powershell
@'
# Framework Architecture

## Overview

AI Website Framework is built around a simple principle:

> The Framework provides the engine.
> Each project provides the business domain.

The Framework never contains business-specific logic.
Business logic is added through reusable domain modules and configuration.

---

# High-Level Runtime Architecture

The Framework consists of four operational runtime engines and an orchestration layer that handle data flow and AI content generation.

```text
Application / Domain Layer
            │
            ▼
  Universal CRUD Engine
            │
            ▼
    Validation Engine
            │
            ▼
       AI Pipeline Subsystem
┌───────────┬───────────────┬────────────────────────┐
│           │               │                        │
│  Prompt   │   AIService   │    StructuredOutput    │
│ Pipeline  │ (Orchestrator)│        Parser          │
│           │               │                        │
└───────────┴───────┬───────┴────────────────────────┘
                    │
                    ▼
          AI Provider Subsystem
(Protocol ── Resilient ── Cache ── OpenRouter)
````

# 1. Core Framework Subsystems

## 1.1 Universal CRUD Engine (`ai_framework.crud`)

Provides persistence abstraction and universal CRUD operations across storage backends (In-Memory, SQLite, Relational DBs) through standardized contexts and results.

## 1.2 Validation Engine (`ai_framework.validation`)

Handles system-wide schema and entity validation. Executes format, type, requirement, and domain delegates (slug, uniqueness, metadata) before data state mutation or persistence.

## 1.3 AI Provider Subsystem (`ai_framework.ai_provider`)

Abstraction layer over LLM providers (Stage 3):

* **`AIProviderProtocol`**: Core contract defining `complete(request: AIRequest) -> AIResponse`.
* **`OpenRouterAdapter`**: Production HTTP client adapter for OpenRouter API.
* **`ResilientProvider`**: Resiliency layer implementing retry mechanisms and provider failovers.
* **`CachedAIProvider`**: Performance layer providing `InMemoryCache` for prompt-response pairs.

## 1.4 AI Pipeline Subsystem (`ai_framework.pipeline`)

Prompt processing, execution, and parsing layer (Stage 4):

* **`PromptPipeline`**: Handles prompt variable substitution, context building, system instruction injection, and pre-flight validation.
* **`StructuredOutputParser`**: Extracts JSON payloads from raw text / Markdown code blocks (`json ...`), validates parsed JSON against schemas or `ValidationEngine`, and wraps failures into `OutputParseError`.
* **`AIService`**: High-level **pure orchestration layer**. Coordinates `PromptPipeline` → `AIProvider` → `StructuredOutputParser`. Contains **zero business logic**. Transparently bubbles up all underlying exceptions (`PromptError`, `AIError`, `OutputParseError`).

# 2. Structural Layers

```text
AI Website Framework
│
├── Framework Core (`ai_framework/`, `framework/core/`)
├── Reusable Components (`framework/components/`)
├── Domain Layer (`framework/domains/` e.g., Nursery, Cafe)
├── Project Generator (`framework/generator/`)
└── Generated Projects (`output/`)
```

### 2.1 Framework Core

Contains universal mechanisms that operate independently of any business domain (routing, configuration, CRUD, validation, AI providers, AI pipeline, localization, storage).

### 2.2 Components

Portable UI and functional building blocks (cards, forms, catalog, gallery, AI assistant).

### 2.3 Domain Layer

Defines business-specific terminology, schemas, rules, entities, and AI prompt contexts for a target industry (e.g., Nursery, Cafe).

### 2.4 Project Generator & Generated Projects

Assembles standalone, independent applications from core engines, selected components, and a target domain configuration.

# 3. Architectural Rules & Error Propagation

1. **Universality First**: Every feature in the Framework Core must be 100% domain-agnostic.

2. **AIService Pure Orchestration Rule**: `AIService` only binds the pipeline, provider, and parser. It must not alter payloads, execute domain validation, or swallow errors.

3. **Transparent Exception Flow**:

   * `PromptError` / `OutputParseError`: Raised during prompt assembly or response parsing.
   * `AIError`: Raised during provider transport/API failures.
   * All errors pass directly through `AIService` to the application/domain caller.

4. **Dependency Direction**:

```text
Generated Project ──► Domain / Components ──► Framework Core
```

Circular dependencies between layers are strictly forbidden.
'@ | Set-Content docs/framework-architecture.md -Encoding UTF8

````


