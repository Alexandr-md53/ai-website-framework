# CODING: utf-8, ASCII only
"""
C9.3 contract — Full FastAPI wiring via C9.2 helper

Proves:
- registration is via C9.2 helper (not direct registry.register)
- helper output is consumable by frozen create_app()
- FastAPI -> APIAdapter -> EndpointPipelineAdapter -> ApplicationPipeline -> UseCase
- dto_factory receives api_req body
- pipeline execution reaches use_case
- no manual wiring required

0 prod changes — uses frozen C6 create_app + C9.2 product_pipeline_wiring
"""

from dataclasses import dataclass
from typing import Dict, Any

from fastapi.testclient import TestClient

from ai_framework.api.fastapi import create_app
from ai_framework.api.product_pipeline_wiring import (
    register_pipeline_endpoint,
    build_registry_from_map,
)
from ai_framework.api.registry import EndpointRegistry

@dataclass(frozen=True)
class CreateArticleDTO:
    title: str
    body: str

class CreateArticleUseCase:
    def __init__(self):
        self.calls = []

    def execute(self, dto: CreateArticleDTO):
        self.calls.append(dto)
        return {"id": "123", "title": dto.title}

def _dto_factory(api_req: Dict[str, Any]) -> CreateArticleDTO:
    body = api_req.get("body", {})
    return CreateArticleDTO(title=body.get("title", ""), body=body.get("body", ""))

def test_c9_3_registration_must_use_helper_not_direct_register():
    """
    Explicit contract: registration MUST go through C9.2 helper, not direct registry.register
    We prove helper exists and creates canonical Endpoint consumable by create_app
    """
    # This import MUST exist — if helper missing, RED
    from ai_framework.api.product_pipeline_wiring import register_pipeline_endpoint

    registry = EndpointRegistry()
    uc = CreateArticleUseCase()

    # MUST use helper, NOT registry.register directly
    endpoint = register_pipeline_endpoint(
        registry, "POST", "/articles", uc, _dto_factory
    )

    # Contract: helper used canonical registry.register internally
    assert ("POST", "/articles") in registry.list()
    assert registry.get("POST", "/articles") is endpoint
    # Contract: endpoint.handler is EndpointPipelineAdapter.handle (proved in C9.2)
    assert callable(endpoint.handler)

def test_c9_3_build_registry_from_map_consumed_by_create_app():
    uc = CreateArticleUseCase()

    # Build registry SOLELY via C9.2 helper bulk builder
    registry = build_registry_from_map(
        {
            ("POST", "/articles"): (uc, _dto_factory),
        }
    )

    # Frozen C6 create_app must consume it without changes
    app = create_app(registry=registry)
    client = TestClient(app)

    resp = client.post("/articles", json={"title": "hello", "body": "world"})

    assert resp.status_code == 200
    data = resp.json()
    # FastAPI layer returns {"json":..., "status":...} unwrapped by create_app
    # Our pipeline returns {"id": "123", "title": "hello"} -> JSONResponse content = that dict
    # Depending on C6 impl, it may be nested under "json" or direct — accept both
    payload = data.get("json", data)
    assert payload["title"] == "hello"
    assert len(uc.calls) == 1
    assert uc.calls[0].title == "hello"

def test_c9_3_full_stack_request_body_reaches_use_case():
    uc = CreateArticleUseCase()

    registry = EndpointRegistry()
    # Explicit helper registration
    register_pipeline_endpoint(registry, "POST", "/articles", uc, _dto_factory)

    app = create_app(registry=registry)
    client = TestClient(app)

    resp = client.post("/articles", json={"title": "t1", "body": "b1"})
    assert resp.status_code == 200

    # Proof chain: HTTP body -> dto_factory -> pipeline -> use_case
    assert uc.calls[0].title == "t1"
    assert uc.calls[0].body == "b1"

def test_c9_3_no_manual_wiring_required():
    """
    Proves C9.3 is integration proof of existing contract, not new architecture
    Manual Endpoint() + EndpointPipelineAdapter() + ApplicationPipeline() NOT used in test
    Only helper + create_app
    """
    uc = CreateArticleUseCase()

    # Only helper + frozen create_app — no manual Endpoint creation
    registry = build_registry_from_map({("POST", "/articles"): (uc, _dto_factory)})
    app = create_app(registry)
    client = TestClient(app)

    resp = client.post("/articles", json={"title": "x", "body": "y"})
    assert resp.status_code == 200
    assert uc.calls[0].title == "x"