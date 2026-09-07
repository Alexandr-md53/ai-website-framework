"""
ai_framework.api - canonical public API for Phase 10.1 A1.4

Delivery Adapter layer: translates HTTP <-> CRUDResult
No application/api duplicate - single source.

Structure:
- contracts.py -> APIResponse, mappers
- adapter.py -> APIAdapter, RequestAdapter, ResponseAdapter
- router.py -> Router, RouteNotFoundError, MethodNotAllowedError
- registry.py -> Registry
- endpoint.py -> Endpoint
"""

from .contracts import (
    APIResponse,
    map_crud_error_to_status_code,
    map_crud_result_to_http_status,
)
from .adapter import APIAdapter, RequestAdapter, ResponseAdapter

# Router layer - core delivery routing
try:
    from .router import Router, RouteNotFoundError, MethodNotAllowedError
except ImportError:
    Router = None  # type: ignore
    RouteNotFoundError = Exception  # type: ignore
    MethodNotAllowedError = Exception  # type: ignore

# Registry layer
try:
    from .registry import APIRegistry, Registry
except ImportError:
    try:
        from .registry import registry as APIRegistry

        Registry = APIRegistry
    except ImportError:
        APIRegistry = None  # type: ignore
        Registry = None  # type: ignore

# Endpoint layer
try:
    from .endpoint import Endpoint, APIEndpoint
except ImportError:
    try:
        from .endpoint import endpoint as Endpoint

        APIEndpoint = Endpoint
    except ImportError:
        Endpoint = None  # type: ignore
        APIEndpoint = None  # type: ignore

__all__ = [
    # Envelope
    "APIResponse",
    "map_crud_error_to_status_code",
    "map_crud_result_to_http_status",
    # Adapters
    "APIAdapter",
    "RequestAdapter",
    "ResponseAdapter",
    # Router
    "Router",
    "RouteNotFoundError",
    "MethodNotAllowedError",
    # Registry
    "APIRegistry",
    "Registry",
    # Endpoint
    "Endpoint",
    "APIEndpoint",
]
