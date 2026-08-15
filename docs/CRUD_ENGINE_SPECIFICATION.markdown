# Universal CRUD Engine Specification

**Document:** `CRUD_ENGINE_SPECIFICATION.md`  
**Status:** Approved (v1.1)  
**Version:** 1.1  
**Target Location:** `ai_framework/crud/`

---

## 1. Purpose

The Universal CRUD Engine provides a standardized, domain-independent mechanism for creating, reading, updating, and deleting entities within the AI Website Framework.

Instead of writing custom CRUD logic for every new business entity (e.g., `Plant`, `Category`, `MenuItem`), the application will rely on this single engine. The engine dynamically adapts its behavior based on the **Metadata Engine** and delegates execution to the **Validation Engine** and **Persistence Layer**.

---

## 2. Architectural Principles

1. **Zero Domain Knowledge:** The CRUD Engine does not know what a "Plant" is. It only knows about "Entities", "Fields", and "Metadata".
2. **Orchestrator, Not Converter:** The CRUD Engine orchestrates the flow. It **does not** perform data normalization or type casting. Input Adapters (Application Layer) must prepare the data format.
3. **Validation-First:** No data reaches the database without passing through the Validation Engine.
4. **Persistence Agnostic:** The CRUD Engine delegates actual storage operations to a `PersistenceProvider` contract, meaning it works regardless of the underlying DB (SQLite, PostgreSQL, MongoDB).
5. **Single Source of Truth:** The engine resides strictly in `ai_framework/crud/`.

---

## 3. Dependencies & Data Flow

The CRUD Engine acts as an orchestrator between the Application Adapter and three Core modules:

```text
                    Application
                         │
                    Input Adapter (Handles type casting/normalization)
                         │
                         ▼
                    CRUD Engine (ai_framework.crud)
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
      Metadata       Validation     Persistence
       Engine          Engine         Contract
                                        │
                                        ▼
                              Persistence Provider
```

---

## 4. Core Interfaces (Contracts)

The engine will expose a primary service class in `ai_framework/crud/engine.py`.

### 4.1. CRUD Engine Methods

```python
class CRUDEngine:
    def __init__(self, metadata_engine, validation_engine, persistence_provider):
        self.metadata = metadata_engine
        self.validation = validation_engine
        self.db = persistence_provider

    def create(self, entity_name: str, data: dict, context: dict = None) -> dict:
        """Creates a new entity record."""
        pass

    def get(self, entity_name: str, entity_id: str | int) -> dict:
        """Retrieves a single entity by its ID. Raises EntityNotFoundError if missing."""
        pass

    def list(self, entity_name: str, filters: dict = None, sort: list = None, pagination: dict = None) -> dict:
        """Retrieves a list of entities matching basic criteria."""
        pass

    def update(self, entity_name: str, entity_id: str | int, data: dict, partial: bool = True) -> dict:
        """Updates an existing entity. Raises EntityNotFoundError if missing."""
        pass

    def delete(self, entity_name: str, entity_id: str | int) -> bool:
        """Deletes an entity. Raises EntityNotFoundError if missing."""
        pass
```

### 4.2. Persistence Provider Contract

The CRUD Engine requires the Persistence Layer to implement a strict contract (`ai_framework/db/contracts.py` or similar):

```python
class PersistenceProvider(Protocol):
    def insert(self, entity_name: str, data: dict) -> dict: ...
    def get_by_id(self, entity_name: str, entity_id: str | int) -> dict | None: ...
    def update(self, entity_name: str, entity_id: str | int, data: dict) -> dict: ...
    def delete(self, entity_name: str, entity_id: str | int) -> bool: ...
    def list(self, entity_name: str, filters: dict, sort: list, pagination: dict) -> list[dict]: ...
```

### 4.3. Standardized Querying (List Operation)

For v1.0 of the CRUD Engine, querying remains simple to avoid building a complex DSL:
* **Filters:** Exact match only (e.g., `{"status": "active", "category_id": 5}`).
* **Sort:** Simple list of fields (e.g., `["-created_at", "name"]`).
* **Pagination:** Basic limit/offset (e.g., `{"limit": 20, "offset": 0}`).

---

## 5. Execution Pipelines

### 5.1. Create Pipeline
1. **Receive:** `CRUDEngine.create("plant", {"name": "Rose", "price": 15})`
2. **Metadata:** Fetch metadata for `entity_name="plant"`. Raise `MetadataNotFoundError` if missing.
3. **Validate:** Pass `data` and metadata schema to `ValidationEngine`. Raise `ValidationError` on failure.
4. **Persist:** Call `PersistenceProvider.insert("plant", validated_data)`.
5. **Return:** Return the newly created record.

### 5.2. Update Pipeline
1. **Receive:** `CRUDEngine.update("plant", 123, {"price": 20})`
2. **Check Exists:** Fetch record `123` via `PersistenceProvider.get_by_id()`. Raise `EntityNotFoundError` if missing.
3. **Metadata:** Fetch metadata for `entity_name="plant"`.
4. **Validate:** Pass partial `data` to `ValidationEngine` (partial validation mode).
5. **Persist:** Call `PersistenceProvider.update("plant", 123, validated_data)`.
6. **Return:** Return the updated record.

### 5.3. Delete Pipeline
1. **Receive:** `CRUDEngine.delete("plant", 123)`
2. **Check Exists:** Fetch record `123` via `PersistenceProvider.get_by_id()`. Raise `EntityNotFoundError` if missing.
3. **Persist:** Call `PersistenceProvider.delete("plant", 123)`.
4. **Return:** `True`.

---

## 6. Error Handling

The CRUD Engine relies on standardized Framework exceptions (to be verified/defined in `ai_framework.core.exceptions`):

* `EntityNotFoundError`: Raised when `get`, `update`, or `delete` targets a non-existent ID.
* `ValidationError`: Propagated from the Validation Engine.
* `MetadataNotFoundError`: Raised if the requested `entity_name` is not registered in the Metadata Engine.
* `PersistenceError`: Raised for database-level constraints (e.g., unique index violations).

---

## 7. Application Adapter Example (Reference Project)

The Reference Project (Plant Nursery) uses an adapter to bridge the HTTP/Domain layer with the Framework:

```python
# site_generation_post/services/plant_service.py
from ai_framework.crud.engine import CRUDEngine

class PlantService:
    def __init__(self, crud_engine: CRUDEngine):
        self.crud = crud_engine

    def add_new_plant(self, raw_http_data: dict):
        # 1. Input Adapter normalizes data (e.g., string to int)
        normalized_data = self._normalize_input(raw_http_data)
        
        # 2. Call the universal Framework engine
        return self.crud.create(entity_name="plant", data=normalized_data)
        
    def _normalize_input(self, data: dict) -> dict:
        # Domain-specific type casting happens here, NOT in CRUD Engine
        if "price" in data:
            data["price"] = float(data["price"])
        return data
```

---

## 8. Definition of Done for Stage 2

1. **Location:** `CRUDEngine` implemented in `ai_framework/crud/engine.py`.
2. **Tests:** 100% test coverage of executable logic in `tests/crud/` (mocking DB and Validation).
3. **Integration:** Tests showing `Metadata -> Validation -> CRUD -> Persistence` flow.
4. **Domain Independence:** Zero domain knowledge (no `Plant` references in tests, use dummy entities like `test_item`).
5. **Exceptions:** All exceptions used are canonical and defined in `ai_framework.core.exceptions`.
