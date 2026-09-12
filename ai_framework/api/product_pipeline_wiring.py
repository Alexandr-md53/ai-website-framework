# CODING: utf-8, ASCII only
"""
C9.2 — minimal product wiring over frozen Registry + Endpoint + EndpointPipelineAdapter

Contract:
- Accepts existing EndpointRegistry (does NOT create alternative Product Registry)
- Creates EndpointPipelineAdapter(pipeline, dto_factory, context_factory)
- Creates Endpoint(path, method, adapter.handle)
- Calls canonical registry.register(method, path, endpoint)

Frozen untouched: C5 ProductInfo, C6 create_app, C7 pipeline boundary, C8 adapter
"""

from __future__ import annotations
from typing import Dict, Tuple, Callable, Any, Optional

from ai_framework.api.registry import EndpointRegistry
from ai_framework.api.endpoint import Endpoint
from ai_framework.api.pipeline_adapter import EndpointPipelineAdapter
from ai_framework.application.pipeline.executor import ApplicationPipeline
from ai_framework.application.pipeline.adapter import UseCaseHandlerAdapter

def register_pipeline_endpoint(
    registry: EndpointRegistry,
    method: str,
    path: str,
    use_case: Any,
    dto_factory: Callable[[Dict[str, Any]], Any],
    context_factory: Optional[Callable] = None,
) -> Endpoint:
    """
    Minimal helper: registry + method + path + pipeline/use_case + dto_factory -> Endpoint registered

    use_case: either object with.execute(dto) or callable(dto)
    """
    if hasattr(use_case, "execute") and callable(getattr(use_case, "execute")):
        handler_callable = use_case.execute
    else:
        handler_callable = use_case

    pipeline_handler = UseCaseHandlerAdapter(handler_callable)
    pipeline = ApplicationPipeline(middlewares=[], handler=pipeline_handler)

    adapter = EndpointPipelineAdapter(pipeline, dto_factory, context_factory)

    endpoint = Endpoint(path=path, method=method, handler=adapter.handle)

    registry.register(method, path, endpoint)

    return endpoint

def build_registry_from_map(
    use_case_map: Dict[Tuple[str, str], Tuple],
) -> EndpointRegistry:
    """
    Bulk builder over canonical register_pipeline_endpoint

    use_case_map: {(method, path): (use_case, dto_factory) or (use_case, dto_factory, context_factory)}
    """
    registry = EndpointRegistry()
    for (method, path), cfg in use_case_map.items():
        if not isinstance(cfg, (list, tuple)):
            raise TypeError(f"Expected tuple for {(method, path)}, got {type(cfg)}")
        if len(cfg) == 2:
            uc, dto_f = cfg
            ctx_f = None
        elif len(cfg) == 3:
            uc, dto_f, ctx_f = cfg
        else:
            raise ValueError(f"Invalid config length for {(method, path)}: {cfg}")

        register_pipeline_endpoint(registry, method, path, uc, dto_f, ctx_f)

    return registry