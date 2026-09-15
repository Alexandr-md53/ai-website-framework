# CODING: utf-8, ASCII only
from __future__ import annotations
import uuid
from typing import Callable, Any
from ai_framework.application.pipeline.contracts import PipelineContext
from ai_framework.application.pipeline.contracts import ApplicationPipelineProtocol

class EndpointPipelineAdapter:
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
        if "headers" in api_request and isinstance(api_request.get("headers"), dict):
            meta["headers"] = api_request.get("headers")
        return PipelineContext(request_id=str(uuid.uuid4()), metadata=meta)

    def handle(self, api_request: dict) -> Any:
        dto = self.dto_factory(api_request)
        context = self.context_factory(api_request)
        if not isinstance(context, PipelineContext):
            raise TypeError("context_factory must return PipelineContext")
        return self.pipeline.execute(dto, context)

__all__ = ["EndpointPipelineAdapter"]

