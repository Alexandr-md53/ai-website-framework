# CODING: utf-8, ASCII only
"""
C9.1 contract tests — FastAPI factory + EndpointPipelineAdapter integration
Proves:
1. FastAPI route -> API dict -> EndpointPipelineAdapter -> Pipeline
2. {id} path param -> DTO
3. query + body -> DTO
4. PipelineContext.metadata contains method/path
5. HTTP error mapping preserved (CRUDResult -> HTTP via api/contracts mapping)

0 production changes — C6.2 create_app untouched, C8 adapter untouched
"""

from dataclasses import dataclass
import pytest

from ai_framework.api.registry import EndpointRegistry
from ai_framework.api.endpoint import Endpoint
from ai_framework.api.pipeline_adapter import EndpointPipelineAdapter
from ai_framework.application.pipeline.contracts import PipelineContext
from ai_framework.application.pipeline.executor import ApplicationPipeline
from ai_framework.application.pipeline.adapter import UseCaseHandlerAdapter

try:
    from fastapi.testclient import TestClient
    from ai_framework.api.fastapi import create_app
    FASTAPI_AVAILABLE = True
except Exception:
    FASTAPI_AVAILABLE = False

@dataclass(frozen=True)
class GetArticleDTO:
    article_id: str
    include_body: bool

@dataclass(frozen=True)
class CreateArticleDTO:
    title: str
    author_id: str

class TrackingUseCase:
    def __init__(self):
        self.calls = []

    def execute(self, dto):
        self.calls.append(dto)
        return {"id": getattr(dto, "article_id", "new"), "title": getattr(dto, "title", "fetched")}

@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_fastapi_route_to_pipeline():
    uc = TrackingUseCase()
    pipeline = ApplicationPipeline(middlewares=[], handler=UseCaseHandlerAdapter(uc.execute))
    def dto_factory(api_req):
        body = api_req.get("body", {})
        return CreateArticleDTO(title=body.get("title", ""), author_id=body.get("author_id", "u1"))
    adapter = EndpointPipelineAdapter(pipeline, dto_factory)
    registry = EndpointRegistry()
    ep = Endpoint(path="/articles", method="POST", handler=adapter.handle)
    registry.register("POST", "/articles", ep)
    app = create_app(registry)
    client = TestClient(app)
    resp = client.post("/articles", json={"title": "Hello", "author_id": "u1"})
    assert resp.status_code in (200, 201)
    assert len(uc.calls) == 1
    assert uc.calls[0].title == "Hello"

@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_path_param_to_dto():
    uc = TrackingUseCase()
    pipeline = ApplicationPipeline(middlewares=[], handler=UseCaseHandlerAdapter(uc.execute))
    def dto_factory(api_req):
        article_id = api_req.get("path_params", {}).get("id") or api_req.get("id")
        query = api_req.get("query", {})
        include = query.get("include_body", False)
        if isinstance(include, str):
            include = include.lower() in ("true", "1")
        return GetArticleDTO(article_id=article_id, include_body=bool(include))
    adapter = EndpointPipelineAdapter(pipeline, dto_factory)
    registry = EndpointRegistry()
    ep = Endpoint(path="/articles/{id}", method="GET", handler=adapter.handle)
    registry.register("GET", "/articles/{id}", ep)
    app = create_app(registry)
    client = TestClient(app)
    resp = client.get("/articles/abc-123?include_body=true")
    assert resp.status_code == 200
    assert uc.calls[0].article_id == "abc-123"
    assert uc.calls[0].include_body is True

@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_query_plus_body_to_dto():
    uc = TrackingUseCase()
    pipeline = ApplicationPipeline(middlewares=[], handler=UseCaseHandlerAdapter(uc.execute))
    def dto_factory(api_req):
        return CreateArticleDTO(title=api_req["body"]["title"], author_id=api_req["query"]["author_id"])
    adapter = EndpointPipelineAdapter(pipeline, dto_factory)
    registry = EndpointRegistry()
    registry.register("POST", "/articles", Endpoint(path="/articles", method="POST", handler=adapter.handle))
    app = create_app(registry)
    client = TestClient(app)
    resp = client.post("/articles?author_id=u99", json={"title": "QB"})
    assert resp.status_code in (200, 201)
    assert uc.calls[0].author_id == "u99"
    assert uc.calls[0].title == "QB"

@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_context_metadata_contains_method_path():
    captured_ctx = {}
    def handler_fn(req, ctx: PipelineContext):
        captured_ctx["ctx"] = ctx
        return {"ok": True}
    pipeline = ApplicationPipeline(middlewares=[], handler=handler_fn)
    adapter = EndpointPipelineAdapter(pipeline, lambda api_req: api_req["body"])
    registry = EndpointRegistry()
    registry.register("GET", "/ping", Endpoint(path="/ping", method="GET", handler=adapter.handle))
    app = create_app(registry)
    client = TestClient(app)
    resp = client.get("/ping")
    assert resp.status_code == 200
    ctx = captured_ctx["ctx"]
    assert isinstance(ctx, PipelineContext)
    assert ctx.metadata.get("method") == "GET"
    assert ctx.metadata.get("path") == "/ping"

@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_http_error_mapping_preserved_via_api_adapter():
    from ai_framework.crud.contracts import CRUDResult, CRUDError
    from ai_framework.api.contracts import map_crud_result_to_http_status

    validation_result = CRUDResult(
        success=False,
        errors=[CRUDError(code="VALIDATION_ERROR", message_key="validation_failed")],
        data=None,
        operation="create"
    )
    assert map_crud_result_to_http_status(validation_result) == 422

    not_found_result = CRUDResult(
        success=False,
        errors=[CRUDError(code="NOT_FOUND", message_key="not_found")],
        data=None
    )
    assert map_crud_result_to_http_status(not_found_result) == 404

    persistence_result = CRUDResult(
        success=False,
        errors=[CRUDError(code="PERSISTENCE_ERROR", message_key="persistence_failed")],
        data=None
    )
    assert map_crud_result_to_http_status(persistence_result) == 500

    def failing_handler(req, ctx):
        return CRUDResult(
            success=False,
            errors=[CRUDError(code="VALIDATION_ERROR", message_key="bad_request", field="title")],
            data=None,
            operation="create"
        )

    pipeline = ApplicationPipeline(middlewares=[], handler=failing_handler)
    adapter = EndpointPipelineAdapter(pipeline, lambda api_req: api_req.get("body", {}))
    registry = EndpointRegistry()
    registry.register("POST", "/articles", Endpoint(path="/articles", method="POST", handler=adapter.handle))
    app = create_app(registry)
    client = TestClient(app)
    resp = client.post("/articles", json={})
    assert resp.status_code == 422

def test_create_app_and_adapter_are_frozen_interfaces():
    from ai_framework.api.fastapi import create_app as ca
    import inspect
    sig = inspect.signature(ca)
    assert "registry" in sig.parameters
    assert hasattr(EndpointPipelineAdapter, "handle")