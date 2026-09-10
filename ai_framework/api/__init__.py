"""
ai_framework.api - canonical public API

Phase 10.1 A1.4 Delivery Adapter + Phase 10.2 C5.1 Product Registry
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
)
from .endpoint import Endpoint

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
    "Endpoint",
]
