# CODING: utf-8, ASCII only
"""
ai_framework.api - canonical public API

Phase 10.1 A1.4 Delivery Adapter + Phase 10.2 C5.1 Product Registry + C5.2 enrichment + C5.5 inspect + C6.1 fastapi factory
"""

from .contracts import (
    APIResponse,
    map_crud_error_to_status_code,
    map_crud_result_to_http_status,
)
from .adapter import APIAdapter, RequestAdapter, ResponseAdapter
from .router import Router, RouteNotFoundError, MethodNotAllowedError
from .registry import (
    EndpointRegistry,
    APIRegistry,
    Registry,
    ProductInfo,
    list_products,
    get_product,
    clear_cache,
)
from .endpoint import Endpoint
from ..tools.scaffold import inspect_project

try:
    from .fastapi import create_app
except Exception:
    create_app = None  # FastAPI not installed in minimal env, factory optional

__all__ = [
    "APIResponse",
    "map_crud_error_to_status_code",
    "map_crud_result_to_http_status",
    "APIAdapter",
    "RequestAdapter",
    "ResponseAdapter",
    "Router",
    "RouteNotFoundError",
    "MethodNotAllowedError",
    "EndpointRegistry",
    "APIRegistry",
    "Registry",
    "ProductInfo",
    "list_products",
    "get_product",
    "clear_cache",
    "Endpoint",
    "inspect_project",
    "create_app",
]
