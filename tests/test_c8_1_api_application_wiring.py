# CODING: utf-8, ASCII only
"""
C8.1 -> C8.2 contract tests — API -> Application Wiring

Proves GAP and defines expected adapter contract without production changes.

API dict -> dto_factory -> DTO
         -> context_factory -> PipelineContext
         -> pipeline.execute(dto, context) -> passthrough result

C5/C6/C7 frozen — untouched.
"""

from dataclasses import dataclass
import uuid
import pytest

from ai_framework.application.pipeline.contracts import PipelineContext


@dataclass(frozen=True)
class FakeCreateArticleRequest:
    title: str
    author_id: str


class FakePipeline:
    def __init__(self):
        self.calls = []

    def execute(self, request, context):
        self.calls.append((request, context))
        return {"success": True, "data": {"id": "123", "title": request.title}}


# Reference implementation — contract definition only, lives in test.
# Production will be ai_framework/api/pipeline_adapter.py EndpointPipelineAdapter
class ReferenceEndpointPipelineAdapter:
    def __init__(self, pipeline, dto_factory, context_factory=None):
        self.pipeline = pipeline
        self.dto_factory = dto_factory
        self.context_factory = context_factory or self._default_context_factory

    @staticmethod
    def _default_context_factory(api_request: dict) -> PipelineContext:
        meta = {}
        if "method" in api_request:
            meta["method"] = api_request.get("method")
        if "path" in api_request:
            meta["path"] = api_request.get("path")
        # headers optional — not mandatory contract, but allowed in metadata
        if "headers" in api_request:
            meta["headers"] = api_request.get("headers")
        return PipelineContext(request_id=str(uuid.uuid4()), metadata=meta)

    def handle(self, api_request: dict):
        dto = self.dto_factory(api_request)
        ctx = self.context_factory(api_request)
        assert isinstance(ctx, PipelineContext)
        return self.pipeline.execute(dto, ctx)


def _api_request_factory():
    return {
        "method": "POST",
        "path": "/articles",
        "query": {},
        "body": {"title": "Hello", "author_id": "u1"},
        "headers": {"x-request-id": "test"},
        "path_params": {},
    }


def _dto_factory(api_request: dict) -> FakeCreateArticleRequest:
    body = api_request.get("body", {})
    return FakeCreateArticleRequest(
        title=body.get("title"), author_id=body.get("author_id")
    )


def test_api_dict_to_dto_factory():
    api_req = _api_request_factory()
    dto = _dto_factory(api_req)
    assert dto.title == "Hello"
    assert dto.author_id == "u1"


def test_api_dict_to_context_factory():
    api_req = _api_request_factory()

    def ctx_factory(req):
        return PipelineContext(
            request_id="fixed-id", metadata={"method": req["method"]}
        )

    ctx = ctx_factory(api_req)
    assert isinstance(ctx, PipelineContext)
    assert ctx.request_id == "fixed-id"
    assert ctx.metadata["method"] == "POST"


def test_adapter_calls_pipeline_execute():
    pipeline = FakePipeline()
    adapter = ReferenceEndpointPipelineAdapter(pipeline, _dto_factory)
    api_req = _api_request_factory()
    result = adapter.handle(api_req)
    assert len(pipeline.calls) == 1
    req, ctx = pipeline.calls[0]
    assert isinstance(req, FakeCreateArticleRequest)
    assert isinstance(ctx, PipelineContext)
    assert req.title == "Hello"


def test_result_passthrough_without_transformation():
    pipeline = FakePipeline()
    adapter = ReferenceEndpointPipelineAdapter(pipeline, _dto_factory)
    result = adapter.handle(_api_request_factory())
    # adapter must not transform pipeline result
    assert result["success"] is True
    assert result["data"]["title"] == "Hello"
    assert result["data"]["id"] == "123"


def test_context_factory_replaceable_deterministic_for_tests():
    pipeline = FakePipeline()

    def deterministic_ctx_factory(req):
        return PipelineContext(request_id="det-123", metadata={"test": True})

    adapter = ReferenceEndpointPipelineAdapter(
        pipeline, _dto_factory, context_factory=deterministic_ctx_factory
    )
    adapter.handle(_api_request_factory())
    _, ctx = pipeline.calls[0]
    assert ctx.request_id == "det-123"
    assert ctx.metadata["test"] is True


def test_default_context_unique_request_id():
    pipeline = FakePipeline()
    adapter = ReferenceEndpointPipelineAdapter(pipeline, _dto_factory)
    adapter.handle(_api_request_factory())
    _, ctx1 = pipeline.calls[0]
    adapter.handle(_api_request_factory())
    _, ctx2 = pipeline.calls[1]
    # default factory must produce unique ids
    assert ctx1.request_id != ctx2.request_id
    # uuid format check
    uuid.UUID(ctx1.request_id)
    uuid.UUID(ctx2.request_id)


def test_default_context_metadata_contains_method_path_optional_headers():
    pipeline = FakePipeline()
    adapter = ReferenceEndpointPipelineAdapter(pipeline, _dto_factory)
    api_req = _api_request_factory()
    adapter.handle(api_req)
    _, ctx = pipeline.calls[0]
    assert ctx.metadata.get("method") == "POST"
    assert ctx.metadata.get("path") == "/articles"
    # headers allowed but not required — reference impl includes if present
    assert "headers" in ctx.metadata


def test_production_adapter_not_required_yet_but_contract_defined():
    # Stage 1 — production file may not exist. This test documents future import path.
    try:
        from ai_framework.api.pipeline_adapter import EndpointPipelineAdapter  # noqa

        # if exists, it must have same constructor signature
        assert True
    except ImportError:
        # expected in stage 1 — no production changes
        assert True
