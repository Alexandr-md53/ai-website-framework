Да. Сейчас `AGENTS.md` как раз нужно заполнить. Я предлагаю сделать его **не копией `START_HERE.md`**, а настоящей инструкцией для AI-агента: что он обязан делать, чего не имеет права делать и какие документы использовать.

Ниже — готовый текст. **Полностью замени содержимое `AGENTS.md` на него.**

````markdown
# AGENTS.md

# AI Website Framework — AI Agent System Instructions

**Document:** `AGENTS.md`  
**Status:** Canonical  
**Version:** 1.0  
**Last Updated:** 2026-08-09

---

# 1. Purpose

This document defines the mandatory operating rules for AI agents
working on the AI Website Framework.

These rules apply to:

- code generation;
- refactoring;
- architecture changes;
- migration work;
- testing;
- documentation;
- analysis of Reference Projects;
- Framework extraction and generalization.

An AI agent MUST follow these rules before modifying the project.

---

# 2. Project Identity

The project is:

**AI Website Framework**

The Framework is a reusable architecture for building websites
and business applications across different domains.

Examples of possible domains:

- Plant Nursery
- Cafe
- Restaurant
- Hotel
- Lawyer
- Dentist
- School
- Beauty Salon
- Portfolio
- and others.

The Framework is not a Plant Nursery framework.

It must remain domain-independent.

---

# 3. Canonical Framework Package

The ONLY canonical Framework package is:

```text
ai_framework/
````

This is the Single Source of Truth for universal Framework functionality.

The package:

```text
framework/
```

has been removed.

AI agents MUST NOT recreate it.

AI agents MUST NOT introduce another package containing duplicate
Framework implementations.

---

# 4. Canonical Import Rule

All Framework imports MUST use:

```python
from ai_framework....
```

Examples:

```python
from ai_framework.validation import ValidationEngine
from ai_framework.metadata import MetadataEngine
from ai_framework.services import ...
```

Forbidden:

```python
from framework....
```

Also forbidden:

```python
sys.path.append(...)
```

or any other path manipulation intended to locate Framework modules.

The Framework must be installed and imported as a normal Python package.

---

# 5. Single Source of Truth

Every universal Framework capability MUST have exactly one
canonical implementation.

Before creating a new module, an AI agent MUST check whether
equivalent functionality already exists.

Never create:

```text
another validation engine
another registry
another metadata engine
another slug service
another asset manager
```

if the capability already exists in:

```text
ai_framework/
```

If duplicate functionality is discovered, stop and report it
before implementing another version.

---

# 6. Framework / Application Boundary

The architectural dependency direction is:

```text
Application
      ↓
ai_framework
```

The Application may use Framework functionality.

The Framework MUST NOT import Application code.

Forbidden:

```text
ai_framework
      ↓
PlantSchema
```

Correct:

```text
PlantSchema
      ↓
ai_framework.validation
      ↓
ValidationEngine
```

Application-specific adapters are allowed.

Framework-specific code must remain unaware of them.

---

# 7. Zero Domain Knowledge

The Framework Core MUST contain zero business-domain knowledge.

The following concepts must NOT be hardcoded into:

```text
ai_framework/
```

Examples:

```text
Plant
Nursery
Watering
Blooming
PlantSchema
Cafe
Burger
HotelRoom
Lawyer
Dentist
```

Domain-specific entities, schemas, mappings and business rules belong
to the Application / Reference Project.

---

# 8. Reference Project

The Plant Nursery project is the current Reference Implementation.

It is used to:

* analyze real business behavior;
* discover reusable architecture;
* validate Framework components;
* perform integration testing;
* prove backward compatibility.

The Reference Project is NOT the Framework.

The Framework must never be modified solely to accommodate
a domain-specific requirement of the Reference Project.

---

# 9. Extraction Principle

When functionality exists in the Reference Project, use the following
process:

```text
Reference Implementation
        ↓
Reference Analysis
        ↓
Business Logic Extraction
        ↓
Generalization
        ↓
Framework Contract
        ↓
Framework Implementation
        ↓
Unit Tests
        ↓
Reference Validation
```

Do not blindly copy Reference Project code into `ai_framework/`.

The goal is to extract the reusable architectural capability,
not the original implementation.

---

# 10. Before Writing Code

Before modifying or creating code, the AI agent MUST:

1. Identify the requested functionality.
2. Determine whether it belongs to Framework or Application.
3. Search for an existing implementation.
4. Read the relevant architecture/specification documents.
5. Check the current migration status.
6. Identify dependencies and integration points.
7. Propose the smallest architectural change necessary.

Do not immediately write code when the architectural boundary
is unclear.

---

# 11. Documentation Hierarchy

The following documents define the project context.

## `START_HERE.md`

Entry point for understanding:

* project mission;
* project structure;
* general development rules;
* Framework / Reference Project relationship.

---

## `docs/framework-structure.md`

Canonical document for:

* physical package structure;
* package boundaries;
* import rules;
* dependency direction;
* Single Source of Truth;
* Framework / Application boundaries.

---

## `docs/framework-architecture.md`

Defines the high-level Framework architecture.

---

## `docs/framework-principles.md`

Defines the architectural principles of the Framework.

---

## `docs/MIGRATION_MAP.md`

Defines:

* extraction roadmap;
* completed modules;
* current migration stage;
* next migration tasks;
* Definition of Done.

---

## `docs/REFERENCE_PROJECT_ANALYSIS.md`

Defines:

* Reference Project analysis;
* Framework / Project separation;
* migration status;
* extraction decisions.

---

## `DEVELOPMENT_WORKFLOW.md`

Defines the development lifecycle and Quality Gate.

---

# 12. Documentation Priority

When working on a specific subsystem, read the most specific
documentation available.

For example:

```text
Package structure
    ↓
framework-structure.md

Validation Engine
    ↓
Validation specifications
    ↓
Validation implementation
    ↓
Validation tests

Migration
    ↓
MIGRATION_MAP.md
    ↓
REFERENCE_PROJECT_ANALYSIS.md
```

Do not make architectural decisions based only on an old conversation.

The repository documentation is the persistent project context.

---

# 13. Validation Engine Rules

The Validation Engine is a canonical Framework subsystem:

```text
ai_framework/validation/
```

It must remain domain-independent.

Domain schemas such as:

```text
PlantSchema
```

belong to the Application / Reference Project.

The Validation Engine provides generic validation mechanisms.

Application adapters provide domain-specific mapping and normalization.

---

# 14. Separation of Responsibilities

AI agents MUST preserve the following separation:

### Framework

Provides:

* contracts;
* engines;
* services;
* registries;
* providers;
* persistence abstractions;
* reusable infrastructure.

### Application

Provides:

* domain entities;
* domain schemas;
* business rules;
* business workflows;
* client-specific mappings;
* client-specific UI;
* client-specific routes.

Do not move business logic into Framework merely because it is
convenient for the current project.

---

# 15. Dependency Rules

Dependencies must be directional.

Higher-level modules may depend on lower-level modules.

Lower-level modules must not depend on higher-level modules.

Circular imports are forbidden.

Before adding an import, consider:

```text
Does this create a dependency cycle?
Does this introduce Application knowledge into Framework?
Does this violate the package boundary?
```

If yes, redesign the integration.

---

# 16. Testing Rules

Every Framework change must be accompanied by appropriate tests.

At minimum:

* existing tests must remain green;
* new behavior must have tests;
* edge cases must be tested;
* integration points must be tested where applicable.

Target:

```text
Executable business logic coverage ≥ 90%
```

Coverage must not be artificially increased by testing
non-executable structural declarations solely for percentage.

---

# 17. Quality Gate

A Framework module is considered complete only when the applicable
Quality Gate is satisfied.

Required checks:

1. Zero Domain Knowledge
2. Unit Tests
3. Framework Specifications Updated
4. NotebookLM Context Ready
5. Roadmap Updated
6. Migration Status Updated
7. Backward Compatibility Verified

Do not mark a migration complete when only the code has been written.

---

# 18. Backward Compatibility

The Reference Project must continue to work after Framework migration.

When replacing existing logic:

```text
Old behavior
     ↓
New Framework component
     ↓
Reference Project validation
```

The migration is not complete until required existing behavior
continues to work.

---

# 19. Migration Decisions

Architectural decisions discovered during migration must be documented.

Examples include:

* type normalization boundaries;
* adapter responsibilities;
* compatibility interfaces;
* multilingual mapping boundaries;
* validation responsibilities;
* package boundaries;
* dependency direction.

Do not leave important architectural decisions only inside
conversation history.

If a decision affects future development, update the appropriate
architecture or migration document.

---

# 20. NotebookLM

NotebookLM is the project's engineering knowledge base.

It is used for:

* approved architecture;
* specifications;
* migration knowledge;
* development standards;
* design decisions;
* stable project context.

NotebookLM is NOT a replacement for the repository.

The repository remains the source of truth for:

* source code;
* tests;
* current implementation;
* canonical documentation.

Only approved and stable documentation should be synchronized
to NotebookLM.

---

# 21. Do Not Guess

If the repository contains conflicting information, do not silently
choose one version.

Identify the conflict and report it.

Examples:

```text
Two implementations of the same module
Conflicting package names
Outdated migration status
Contradictory specifications
Missing dependency
```

Resolve the architectural conflict before continuing.

---

# 22. Minimal Change Principle

Prefer the smallest change that correctly solves the problem.

Do not:

* rewrite working modules without architectural justification;
* rename packages unnecessarily;
* introduce new abstractions without need;
* duplicate existing functionality;
* modify unrelated files.

Every architectural change should have a reason.

---

# 23. AI Agent Working Style

The AI agent should work in the following order:

```text
UNDERSTAND
    ↓
INSPECT
    ↓
CLASSIFY
    ↓
PLAN
    ↓
IMPLEMENT
    ↓
TEST
    ↓
DOCUMENT
    ↓
VERIFY
```

### Understand

Determine what the user wants.

### Inspect

Check the actual repository structure and relevant files.

### Classify

Determine:

```text
CORE
CORE SERVICE
PLUGIN
APPLICATION
REFERENCE PROJECT
```

### Plan

Explain the intended change before making a substantial modification.

### Implement

Make the smallest correct change.

### Test

Run relevant tests.

### Document

Update the appropriate documentation.

### Verify

Confirm that architecture, tests and migration status remain
consistent.

---

# 24. Do Not Reintroduce Removed Architecture

The following architectural decision is already finalized:

```text
framework/
```

was a duplicate Framework package.

It has been removed.

AI agents MUST NOT:

* recreate `framework/`;
* copy `ai_framework/` into another package;
* restore duplicate Validation Engine files;
* introduce compatibility aliases that recreate the same ambiguity.

The canonical package remains:

```text
ai_framework/
```

---

# 25. Final Architectural Rules

The following rules are non-negotiable:

```text
1. One Framework.
2. One canonical package: ai_framework.
3. One implementation of each universal capability.
4. Zero domain knowledge in Framework Core.
5. Application depends on Framework.
6. Framework never depends on Application.
7. No duplicate modules.
8. No sys.path hacks.
9. No circular imports.
10. Reference Project validates Framework.
11. Tests must remain green.
12. Architectural decisions must be documented.
13. Do not guess when documentation conflicts.
14. Do not reintroduce removed architecture.
```

---

# 26. Final Principle

> **Build universal architecture once.
> Keep business logic in the Application.
> Extract reusable capabilities into `ai_framework`.
> Never duplicate solved problems.**

The AI agent must preserve this architecture throughout all future
development.

````

### Что теперь у нас получится

`AGENTS.md` будет выполнять именно роль **System Instruction для AI-агента**.

А `START_HERE.md` останется человеческим входом в проект.

То есть не надо дублировать всё в `START_HERE`:

```text
AGENTS.md
   ↓
КАК AI должен работать

START_HERE.md
   ↓
ЧТО это за проект

framework-structure.md
   ↓
КАК устроены пакеты

MIGRATION_MAP.md
   ↓
КУДА движемся

REFERENCE_PROJECT_ANALYSIS.md
   ↓
ЧТО и почему извлекаем

DEVELOPMENT_WORKFLOW.md
   ↓
КАК проходит полный цикл разработки
````

**После сохранения `AGENTS.md` я бы уже не менял его без архитектурной причины.** Это будет наш постоянный набор правил для всех следующих чатов и AI-агентов.
