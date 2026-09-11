# CODING: utf-8, ASCII only
"""
C8.2 impl tests — real EndpointPipelineAdapter wired to ApplicationPipeline
"""

from dataclasses import dataclass
import uuid

from ai_framework.api.pipeline_adapter import EndpointPipelineAdapter
from ai_framework.application.pipeline.contracts import PipelineContext
from ai_framework.application.pipeline.executor import ApplicationPipeline
from ai_framework.application.pipeline.adapter import UseCaseHandlerAdapter
from ai_framework.api.endpoint import Endpoint
from ai_framework.api.registry import EndpointRegistry
from ai_framework.api.router import Router


@dataclass(frozen=True)
class CreateDTO:
    title: str


class FakeUseCase:
    def __init__(self):
        self.calls = []

    def execute(self, req: CreateDTO):
        self.calls.append(req)
        return {"success": True, "dto_title": req.title}


def _dto_factory(api_req):
    return CreateDTO(title=api_req["body"]["title"])


def test_real_adapter_with_pipeline():
    uc = FakeUseCase()
    handler = UseCaseHandlerAdapter(uc.execute)
    pipeline = ApplicationPipeline(middlewares=[], handler=handler)
    adapter = EndpointPipelineAdapter(pipeline, _dto_factory)

    api_req = {
        "method": "POST",
        "path": "/articles",
        "body": {"title": "X"},
        "query": {},
        "headers": {},
        "path_params": {},
    }
    result = adapter.handle(api_req)
    assert result["dto_title"] == "X"
    assert len(uc.calls) == 1


def test_real_adapter_context_factory_injection():
    uc = FakeUseCase()
    pipeline = ApplicationPipeline(
        middlewares=[], handler=UseCaseHandlerAdapter(uc.execute)
    )

    def ctx_factory(req):
        return PipelineContext(request_id="fixed-999", metadata={"custom": True})

    adapter = EndpointPipelineAdapter(
        pipeline, _dto_factory, context_factory=ctx_factory
    )
    result = adapter.handle(
        {
            "method": "GET",
            "path": "/t",
            "body": {"title": "Y"},
            "query": {},
            "headers": {},
            "path_params": {},
        }
    )
    assert result["dto_title"] == "Y"


def test_real_adapter_default_uuid_unique():
    # pipeline returns context itself to inspect
    pipeline = ApplicationPipeline(middlewares=[], handler=lambda req, ctx: ctx)
    adapter = EndpointPipelineAdapter(pipeline, _dto_factory)

    ctx1 = adapter.handle(
        {
            "method": "POST",
            "path": "/a",
            "body": {"title": "a"},
            "query": {},
            "headers": {},
            "path_params": {},
        }
    )
    ctx2 = adapter.handle(
        {
            "method": "POST",
            "path": "/a",
            "body": {"title": "a"},
            "query": {},
            "headers": {},
            "path_params": {},
        }
    )
    assert isinstance(ctx1, PipelineContext)
    assert isinstance(ctx2, PipelineContext)
    assert ctx1.request_id != ctx2.request_id
    uuid.UUID(ctx1.request_id)


def test_adapter_used_as_endpoint_handler():
    uc = FakeUseCase()
    pipeline = ApplicationPipeline(
        middlewares=[], handler=UseCaseHandlerAdapter(uc.execute)
    )
    adapter = EndpointPipelineAdapter(pipeline, _dto_factory)

    registry = EndpointRegistry()
    ep = Endpoint(path="/articles", method="POST", handler=adapter.handle)
    registry.register("POST", "/articles", ep)

    router = Router(registry)
    api_dict = {
        "method": "POST",
        "path": "/articles",
        "query": {},
        "body": {"title": "Wired"},
        "headers": {},
        "path_params": {},
    }
    result = router.route("POST", "/articles", api_dict)
    assert result["dto_title"] == "Wired"
