# AI Website Framework

AI Website Framework is a modular framework for building AI-powered business websites.

Its purpose is to separate universal website functionality from business-specific logic, allowing new projects to be created quickly while sharing a common architecture.

The Framework is designed around reusable components rather than single-purpose applications.

## Vision

Traditional websites are usually developed independently.

AI Website Framework takes a different approach.

Each new website is created from the same Framework by combining:

- Framework Core (`ai_framework`)
- Domain configuration
- Reusable components
- Business-specific content and showcases (`showcases`)

The result is an independent website that can continue evolving without affecting other projects.

## Principles

- **Framework first:** Business logic never leaks back into the core framework.
- **Components before pages:** Build reusable blocks before assembly.
- **Configuration before hardcoding:** Domain metadata over custom structural code.
- **Reusability over duplication:** Every core feature serves multiple business domains.
- **AI as a native architecture element:** Built-in AI integration capabilities.

## Business Showcases (Phase 9 — FROZEN)

The framework's universality is proven by three distinct domain showcases built on top of the same core:

1. **Plant Nursery Showcase:** Hierarchy, Media assets, Inventory management, Search criteria.
2. **Cafe Showcase:** Dynamic UI Metadata, Status Lifecycle workflows, Price Modifiers, RBAC.
3. **Lawyer / Service Showcase:** M2M Graphs, Complex Validation Engines, Role-based Data Isolation.

## Repository Structure

- `ai_framework/` — Core framework code (domain-agnostic).
- `showcases/` — Reference business applications built using the framework.
- `tests/` — Test suites covering framework core (407 tests) and domain showcases (37 tests).

## Status

**Phase 9 (Business Showcases) — COMPLETED / FROZEN**

- Total Project Tests: **444 / 444 GREEN** (100% pass)
- Showcase Validation: **37 / 37 GREEN**
- Architectural isolation between `ai_framework` and domain `showcases` fully verified.

## Running Tests

Run the full test suite (Framework + Showcases):

## Product Backlog

- [Backlog Vertical Features](docs/product/backlog-vertical-features.md) — next: finish docs_site as Type C full demo
- Baseline: cd0b9a9 / 663 passed
- Architecture Stable: phase-12-architecture-stable (90723b3) — framework frozen, only proven generic boundaries

```bash
python -m pytest
## Product Backlog

- [Backlog Vertical Features](docs/product/backlog-vertical-features.md) � next: finish docs_site as Type C full demo
- Baseline: cd0b9a9 / 663 passed
- Architecture Stable: phase-12-architecture-stable (90723b3) � framework frozen
