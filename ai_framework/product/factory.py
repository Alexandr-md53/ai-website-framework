# CODING: utf-8, ASCII only
"""
C10.1 Product Assembly Factory

C5 ProductInfo -> C9.2 build_registry_from_map() -> C6 create_app() -> FastAPI

Constraints:
- No filesystem scanning
- No auto-discovery
- Uses existing C9.2 builder and frozen C6 create_app
- ProductInfo is metadata input only
"""

from __future__ import annotations

from typing import Dict, Tuple, Callable, Any

from ai_framework.product_registry import ProductInfo
from ai_framework.api.product_pipeline_wiring import build_registry_from_map
from ai_framework.api.fastapi import create_app

def build_app_from_product_info(
    info: ProductInfo,
    use_case_map: Dict[Tuple[str, str], Tuple[Any, Callable[[Dict[str, Any]], Any]]],
):
    """
    Build FastAPI app from ProductInfo metadata + explicit use_case_map

    Args:
        info: C5 ProductInfo — metadata only, no FS scanning
        use_case_map: {(METHOD, path): (use_case, dto_factory)} — explicit wiring

    Returns:
        FastAPI app via C9.2 builder + C6 frozen create_app
    """
    # info is accepted as metadata — not used for scanning
    _ = info  # explicit acknowledgment of metadata input

    registry = build_registry_from_map(use_case_map)
    app = create_app(registry=registry)
    return app