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