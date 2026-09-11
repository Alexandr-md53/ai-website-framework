# CODING: utf-8, ASCII only
"""
ai_framework.api.pipeline_adapter - API -> Application Wiring (C8.2)

Bridges frozen API layer (Endpoint dict) to frozen ApplicationPipeline.

Contract:
  api_request: dict{method, path, query, body, headers, path_params}
    -> dto_factory(api_request) -> typed DTO
    -> context_factory(api_request) -> PipelineContext
    -> pipeline.execute(dto, context) -> raw result passthrough

No business logic, no DTO mapping semantics, no frozen modifications.
"""

from __future__ import annotations
import uuid
from typing import Callable, Any

from ai_framework.application.pipeline.contracts import PipelineContext
from ai_framework.application.pipeline.contracts import ApplicationPipelineProtocol


class EndpointPipelineAdapter:
    """
    Adapts API dict request to ApplicationPipeline execution.

    Args:
        pipeline: ApplicationPipelineProtocol â€” frozen C7.2
        dto_factory: Callable[[dict], TRequest] â€” converts api dict to typed DTO
        context_factory: Callable[[dict], PipelineContext] | None â€” default uses uuid4
    """

    def __init__(
        self,
        pipeline: ApplicationPipelineProtocol,
        dto_factory: Callable[[dict], Any],
        context_factory: Callable[[dict], PipelineContext] | None = None,
    ) -> None:
        self.pipeline = pipeline
        self.dto_factory = dto_factory
        self.context_factory = context_factory or self._default_context_factory

    @staticmethod
    def _default_context_factory(api_request: dict) -> PipelineContext:
        meta: dict = {}
        if "method" in api_request:
            meta["method"] = api_request.get("method")
        if "path" in api_request:
            meta["path"] = api_request.get("path")
        # headers optional in metadata â€” not mandatory, but allowed
        if "headers" in api_request and isinstance(api_request.get("headers"), dict):
            meta["headers"] = api_request.get("headers")
        # query / path_params can be added if downstream needs, but not required
        return PipelineContext(request_id=str(uuid.uuid4()), metadata=meta)

    def handle(self, api_request: dict) -> Any:
        dto = self.dto_factory(api_request)
        context = self.context_factory(api_request)
        if not isinstance(context, PipelineContext):
            raise TypeError("context_factory must return PipelineContext")
        return self.pipeline.execute(dto, context)


__all__ = ["EndpointPipelineAdapter"]
