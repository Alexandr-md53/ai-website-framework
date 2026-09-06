"""
ai_framework.crud - canonical public API for Phase 10.1 A1.2

Two engines intentionally:
- UniversalCRUDEngine: generic, entity_name + dict, returns CRUDResult
- CRUDEngine: schema-aware, reads __slug_config__, returns dict

Two providers:
- InMemoryPersistenceProvider (test/prototype)
- SQLitePersistenceProvider (prod) - both implement PersistenceProviderProtocol
"""

from .contracts import CRUDContext, CRUDResult, CRUDError, PersistenceProviderProtocol
from .engine import UniversalCRUDEngine
from .crud_engine import CRUDEngine
from .persistence import InMemoryPersistenceProvider
from .sqlite_persistence import SQLitePersistenceProvider

__all__ = [
    "CRUDContext",
    "CRUDResult",
    "CRUDError",
    "PersistenceProviderProtocol",
    "UniversalCRUDEngine",
    "CRUDEngine",
    "InMemoryPersistenceProvider",
    "SQLitePersistenceProvider",
]
