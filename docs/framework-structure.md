# AI Website Framework Physical Structure

**Document:** `framework-structure.md`  
**Status:** Stable  
**Version:** 1.2  
**Role:** Canonical  
**Last Updated:** 2026-08-18  
**Verified Against:** `dd543f7`  

---

## 1. Purpose

This document defines the canonical physical structure of the AI Website Framework, including package boundaries, module statuses, implemented vs. planned layers, physical location mappings, and import dependency rules.

---

## 2. Canonical Framework Package

The single canonical Framework package is:

```text
ai_framework/
All universal Framework functionality MUST exist inside this package. Legacy or duplicated packages are strictly prohibited.

3. Current Physical Package Map
Plaintext
ai_framework/
│
├── crud/            ← CRUDEngine (Facade), UniversalCRUDEngine & Persistence Providers
├── validation/      ← ValidationEngine (Validation-First Boundary)
├── ai_provider/     ← AI Provider Subsystem (Adapters, Resilience, Cache)
├── pipeline/        ← AI Pipeline Subsystem & AIService Orchestrator
├── localization/    ← Localization Engine (LOC_01)
└── services/        ← Domain-Agnostic Infrastructure Services
    ├── slug/        ← Slug Service (SlugGenerator, AsyncSlugOrchestrator)
    └── asset/       ← Asset Manager (ASM_01)
4. Implemented Subsystems
4.1 CRUD Engine & Persistence Subsystem
Location: ai_framework/crud/

CRUDEngine (engine.py): High-level schema-aware facade layer that separates low-level persistence operations from domain-specific business logic. Operates strictly on structural metadata contracts such as __slug_config__ without knowledge of domain entities or business semantics. Orchestrates validation (ValidationEngine), low-level CRUD (UniversalCRUDEngine), and slug lifecycle management (AsyncSlugOrchestrator).

UniversalCRUDEngine (universal.py): Low-level storage abstraction executing universal CRUD operations across backend persistence providers without domain or slug awareness.

PersistenceProvider (ai_framework/crud/): Storage backend contract and implementations (e.g., In-Memory, SQLite) providing concrete persistence execution abstractions.

ValidationEngine (ai_framework/validation/): Validation boundary executing schema integrity checks prior to data persistence (Validation-First).

AsyncSlugOrchestrator (ai_framework/services/slug/): Asynchronous slug manager providing custom slug validation and automatic collision resolution (-2, -3). Physically located in services/slug/ as a reusable infrastructure component consumed by CRUDEngine.

4.2 Slug Service
Location: ai_framework/services/slug/

Status: Implemented & Verified (SLG_01)

Provides asynchronous slug generation, collision detection/resolution, and URL identifier resolution through SlugGenerator and AsyncSlugOrchestrator. Acts as an independent infrastructure service consumed by the CRUD facade.

4.3 Validation Engine
Location: ai_framework/validation/

Status: Implemented & Verified (VL_01)

Provides schema-driven validation, built-in type/format validators, context management, and optional delegate hooks for external validation concerns such as slug and uniqueness checks.

4.4 Localization Engine
Location: ai_framework/localization/

Status: Implemented & Verified (LOC_01)

Handles multilingual translation resolution, fallback mechanisms, and locale context state.

4.5 Asset Manager
Location: ai_framework/services/asset/

Status: Implemented & Verified (ASM_01)

Manages static and dynamic media assets, paths, and lifecycle storage.

4.6 AI Provider Subsystem
Location: ai_framework/ai_provider/

Status: Implemented & Verified

Provides LLM protocol abstractions (AIProviderProtocol), production adapters (OpenRouterAdapter), resilience handlers (ResilientProvider), and response caching (CachedAIProvider).

4.7 AI Pipeline Subsystem
Location: ai_framework/pipeline/

Status: Implemented & Verified

Provides prompt construction (PromptPipeline), structured output parsing (StructuredOutputParser), and pure LLM workflow orchestration (AIService). Depends directly on ai_provider/.

5. Infrastructure Services Boundary (ai_framework/services/)
Domain-Agnostic Policy: The ai_framework/services/ package MUST contain only domain-agnostic, reusable infrastructure services (e.g., slug, asset).

No Domain Pollution: Placing domain-specific logic, business entities, or domain services (e.g., plant_service, product_service, article_service) inside ai_framework/services/ is strictly forbidden.

Physical vs. Architectural Role: Physical placement in services/ does not grant business ownership. Infrastructure services are independent utility layers consumed by high-level facades or application workflows.

6. Import Rules & Isolation Boundaries
6.1 Canonical Import Rule
All imports MUST reference ai_framework and its exact subsystem packages. Relative or legacy import paths are strictly prohibited.

Python
# CORRECT
from ai_framework.crud import CRUDEngine, UniversalCRUDEngine
from ai_framework.services.slug import AsyncSlugOrchestrator, SlugGenerator
from ai_framework.validation import ValidationEngine
from ai_framework.ai_provider import AIRequest, AIResponse
from ai_framework.pipeline import AIService
Python
# FORBIDDEN (Legacy package structure)
from framework.crud import ...

# FORBIDDEN (Path manipulation hacks)
import sys; sys.path.append(...)
6.2 Subsystem Isolation Rules
CRUD ↔ AI Pipeline Independence: ai_framework/crud/ and ai_framework/pipeline/ (or ai_framework/ai_provider/) operate as completely independent branches. Direct cross-imports between CRUD and AI subsystems are strictly prohibited.

Pipeline → AI Provider Dependency: ai_framework/pipeline/ may import from ai_framework/ai_provider/. Reverse dependency (ai_provider → pipeline) is forbidden.

Circular Import Prohibition: Circular dependencies between any packages or subsystems are strictly forbidden.

7. Dependency Directions
Note: Dependency directions shown in this section describe component-level dependencies; physical package boundaries are defined separately in Section 3.

7.1 Current State Dependency Flow (Stage 1–5)
Plaintext
CRUDEngine (Facade)
   ├──► ValidationEngine (ai_framework/validation)
   ├──► AsyncSlugOrchestrator (ai_framework/services/slug)
   └──► UniversalCRUDEngine (ai_framework/crud)
           └──► PersistenceProvider (ai_framework/crud)

AIService (Pipeline Orchestrator)
   └──► AIProviderProtocol (ai_framework/ai_provider)
7.2 Target Clean Architecture Dependency Flow (Stage 6+)
Plaintext
                 Application Layer [Planned Stage 6]
                        │
                        ▼
                   Domain Layer [Planned Stage 6]
              (Contracts / Ports / Interfaces)
                        ▲
                        │
          ┌─────────────┴─────────────┐
          │                           │
   Framework Infrastructure      AI Infrastructure
          │                           │
   ┌──────┼────────┐            ┌─────┴─────┐
   ▼      ▼        ▼            ▼           ▼
  CRUD  Validation Services   Pipeline   AI Provider
8. Planned Architectural Layers (Stage 6+)
The following packages represent planned architectural layers for Stage 6 and beyond. They are explicitly separated from the currently implemented physical package map:

Plaintext
ai_framework/
├── domain/            ← [STAGE 6] Pure Domain Entities & Contracts (Zero Infrastructure Dependencies)
├── application/       ← [STAGE 6] Application Services & Pipeline Workflows
├── core/              ← Shared Registry, System Contracts & Settings
├── metadata/          ← Metadata Engine & Driven Schema Parsers
├── generators/        ← Content & Site Generator Pipeline
└── plugins/           ← Extension Systems & Plugin Contracts