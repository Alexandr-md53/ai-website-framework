# Changelog

All notable changes to AI Website Framework are documented in this file.

The project follows semantic versioning.

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