# AI Website Framework Structure

**Document:** `framework-structure.md`  
**Status:** Canonical  
**Version:** 1.1  
**Last Updated:** 2026-08-13

---

## 1. Purpose

This document defines the canonical physical structure of the AI Website Framework, including:

- package boundaries;
- implemented vs planned module responsibilities;
- dependency and import rules;
- Framework / Application boundary;
- Single Source of Truth policy.

---

## 2. Canonical Framework Package

The only canonical Framework package is:

```text
ai_framework/
All universal Framework functionality MUST exist inside this package.The legacy duplicated framework/ package has been completely removed.Plaintextai_framework/
      ↓
Single Source of Truth

## 3. Physical Package Map (Current vs Planned)To maintain clarity and prevent documentation drift, modules are strictly categorized by their current implementation status:Plaintextai_framework/
│
├── [CURRENT / IMPLEMENTED]
│   ├── crud/           ← Universal CRUD Engine (Stages 1-2)
│   ├── validation/     ← Validation Engine (Stage 2)
│   ├── ai_provider/    ← AI Provider Subsystem (Stage 3)
│   └── pipeline/       ← AI Pipeline & Orchestration (Stage 4)
│
└── [PLANNED / TARGET ARCHITECTURE]
    ├── core/           ← Shared Registry, Contracts & Settings
    ├── metadata/       ← Metadata Engine
    ├── generators/     ← Content Generator Pipeline
    ├── plugins/        ← Plugin Architecture
    ├── localization/   ← Multilingual Engine
    └── services/       ← Core Services (Slug, Asset Manager)

4. Implemented Subsystems (Current State)
4.1 Universal CRUD EngineLocation: ai_framework/crud/Status: Implemented & VerifiedProvides database-agnostic CRUD operations, generic handlers, and persistent storage abstractions.
4.2 Validation EngineLocation: ai_framework/validation/Status: Implemented & VerifiedProvides schema validation, built-in rules, entity integrity checks, context handling, and delegate injection without binding to specific business entities.
4.3 AI Provider Subsystem (Stage 3)
-Location: ai_framework/ai_provider/Status: Implemented & VerifiedContains abstractions and provider implementations for LLM interaction:contracts.py: AIProviderProtocol, AIRequest, AIResponse, ChatMessage, TokenUsage, FinishReason, AIError.adapters/: OpenRouterAdapter.resilience/: ResilientProvider (retry / fallback mechanisms).cache/: CachedAIProvider (InMemoryCache).
4.4 AI Pipeline Subsystem (Stage 4)
-Location: ai_framework/pipeline/Status: Implemented & VerifiedContains prompt construction, parsing, and orchestration components:
-PromptPipeline: Variable substitution, context injection, pre-flight prompt validation.
-StructuredOutputParser: Markdown/JSON extraction, schema validation, ValidationEngine integration.
-AIService: Pure orchestration layer binding Pipeline → Provider → Parser.

5. Target Subsystems (Planned State)The following packages are reserved for future architectural expansion and MUST NOT be imported until implemented:SubsystemLocationTarget PurposeCore Infrastructureai_framework/core/Central registry, system settings, base exceptionsMetadata Engineai_framework/metadata/Structural entity & form descriptionsGenerator Pipelineai_framework/generators/Multi-step build & content renderingPlugin Systemai_framework/plugins/Extension contracts and registrationLocalization Engineai_framework/localization/Multilingual string resolutionCore Servicesai_framework/services/Universal utilities (Asset Manager, Slugifier)

6. Import Rules & BoundariesCanonical Import RuleAll imports MUST reference ai_framework and its exact subsystem packages:Python# CORRECT
from ai_framework.ai_provider import AIRequest, AIResponse
from ai_framework.pipeline import AIService, PromptPipeline
from ai_framework.validation import ValidationEngine
Forbidden ImportsPython# FORBIDDEN (Legacy package)
from framework.ai import ...

# FORBIDDEN (Outdated subsystem naming)
from ai_framework.ai import ...
Path ManipulationSystem path hacks (sys.path.append(...)) are strictly prohibited. The framework must be installed or referenced via standard package resolution.

7. Dependency DirectionPlaintextApplication / Domain Layer
            │
            ▼
      ai_framework/
  ┌─────────┴─────────┐
  ▼                   ▼
pipeline        ai_provider
  │                   ▲
  └───────────────────┘
Framework Core modules MUST NEVER depend on Application code.AIService Orchestrator depends on PromptPipeline, AIProviderProtocol, and StructuredOutputParser.Circular dependencies across modules are strictly forbidden.8. Summary RuleOne Framework. One canonical package (ai_framework). Actual state matches 241 passing tests.