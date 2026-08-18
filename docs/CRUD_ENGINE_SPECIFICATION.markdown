# Universal CRUD Engine & Slug Facade Specification

**Document:** `CRUD_ENGINE_SPECIFICATION.md`  
**Status:** Approved (v1.2)  
**Version:** 1.2  
**Target Location:** `ai_framework/crud/`

---

## 1. Purpose

The CRUD Engine provides a standardized, domain-independent facade for creating, reading, updating, and deleting entities within the AI Website Framework.

It operates as a high-level facade layer (`CRUDEngine`) that coordinates low-level storage operations (`UniversalCRUDEngine`), validation execution (`ValidationEngine`), and asynchronous slug lifecycle management (`AsyncSlugOrchestrator`).

---

## 2. Architectural Principles & Facade Role

1. **Zero Domain Knowledge:** Operates strictly on schemas, entities, and structural metadata contracts (`__slug_config__`). The engine interprets `source_field`, `slug_field`, and uniqueness constraints without any awareness of domain-specific business concepts (such as `plant`, `article`, `product`, or `doctor`).
2. **Facade & Orchestrator:** `CRUDEngine` does not execute raw DB operations itself; it delegates low-level persistence to `UniversalCRUDEngine` and URL identifier resolution to `AsyncSlugOrchestrator`.
3. **Validation-First:** All mutations pass through `ValidationEngine` before state persistence.
4. **Persistence Agnostic:** Delegates storage to `PersistenceProvider` abstractions via `UniversalCRUDEngine`.

---

## 3. Data Flow & Subsystem Binding

```text
                     Application / Domain Layer
                                 │
                                 ▼
                         CRUDEngine (Facade)
           ┌─────────────────────┼─────────────────────┐
           ▼                     ▼                     ▼
 Validation Engine     UniversalCRUDEngine    AsyncSlugOrchestrator
                           (Low-Level CRUD)      (Slug Service)
                                 │
                                 ▼
                        Persistence Provider
4. Slug Generation & Collision Contracts
When creating or updating entities with slug requirements (__slug_config__), CRUDEngine enforces the following strict rules via AsyncSlugOrchestrator:

4.1 Explicit Custom Slug Collision
If data contains an explicitly specified custom slug (e.g., {"slug": "my-custom-url"}):

If the slug already exists in storage for the given entity type, CRUDEngine strictly raises ValueError.

Custom slugs are treated as explicit user intent and are never mutated automatically.

4.2 Auto-Generated Slug Collision Resolution
If a slug is automatically generated from a target field (e.g., title -> my-article-title):

If a collision occurs, AsyncSlugOrchestrator resolves it using iterative numerical suffixes:

my-article-title (collided)

my-article-title-2 (check uniqueness)

my-article-title-3 (assigned upon finding an available slot)

5. Execution Pipelines
5.1 Create Pipeline
Receive: CRUDEngine.create(entity_name, data)

Validate: Execute schema validation via ValidationEngine.

Resolve Slug:

If custom slug provided → validate uniqueness. Raise ValueError on collision.

If auto slug → generate from source field. Resolve collisions via numerical suffixes (-2, -3).

Persist: Pass final record to UniversalCRUDEngine.insert().

Return: Created record with resolved slug and generated ID.

5.2 Update Pipeline
Receive: CRUDEngine.update(entity_name, entity_id, data)

Fetch Existing: Verify entity presence via UniversalCRUDEngine.get_by_id(). Raise EntityNotFoundError if missing.

Handle Slug Update:

Preservation Policy (SEO-friendly): If the field mapped to source_field changes (e.g., title changes from "Red Rose" to "White Rose"), the existing slug remains unchanged by default to preserve URL stability.

Explicit Update: If a new slug is explicitly provided in the update payload, validate uniqueness against other records. If it collides with an existing record, raise ValueError.

Persist: Update record via UniversalCRUDEngine.update().

Return: Updated record.

6. Definition of Done
CRUDEngine acts as a facade over UniversalCRUDEngine and AsyncSlugOrchestrator.

Test suite explicitly verifies explicit slug collision handling (ValueError), auto-slug suffix resolution (-2, -3), and slug preservation on updates.

Zero domain dependencies present in ai_framework/crud/.