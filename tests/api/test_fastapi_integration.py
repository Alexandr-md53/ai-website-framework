import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from ai_framework.api.registry import EndpointRegistry
from ai_framework.api.router import Router
from ai_framework.api.adapter import APIAdapter
from ai_framework.api.contracts import CRUDResult, CRUDError
from ai_framework.api.endpoint import Endpoint


@pytest.fixture
def setup_app():
    app = FastAPI()
    registry = EndpointRegistry()
    router = Router(registry)
    adapter = APIAdapter(router)
    return app, registry, adapter


def test_get_success_200(setup_app):
    app, registry, adapter = setup_app

    def handler(request):
        return CRUDResult(success=True, data={"id": 1}, errors=[])

    endpoint = Endpoint(path="/api/v1/plants", method="GET", handler=handler)
    registry.register("GET", "/api/v1/plants", endpoint)

    @app.get("/api/v1/plants")
    async def plants(request: Request):
        http_request = {
            "query": dict(request.query_params),
            "body": {},
            "headers": dict(request.headers),
            "path_params": {},
        }
        result = adapter.handle_request("GET", "/api/v1/plants", http_request)
        return JSONResponse(content=result["json"], status_code=result["status"])

    client = TestClient(app)
    response = client.get("/api/v1/plants")
    assert response.status_code == 200
    assert response.json()["data"]["id"] == 1


def test_post_success_201(setup_app):
    app, registry, adapter = setup_app

    def handler(request):
        return CRUDResult(success=True, data={"id": 99}, errors=[], operation="create")

    endpoint = Endpoint(path="/api/v1/plants", method="POST", handler=handler)
    registry.register("POST", "/api/v1/plants", endpoint)

    @app.post("/api/v1/plants")
    async def plants(request: Request):
        body = await request.json()
        http_request = {
            "query": dict(request.query_params),
            "body": body,
            "headers": dict(request.headers),
            "path_params": {},
        }
        result = adapter.handle_request("POST", "/api/v1/plants", http_request)
        return JSONResponse(content=result["json"], status_code=result["status"])

    client = TestClient(app)
    response = client.post("/api/v1/plants", json={"name": "rose"})
    assert response.status_code == 201
    assert response.json()["data"]["id"] == 99


def test_post_validation_error_422(setup_app):
    app, registry, adapter = setup_app

    def handler(request):
        error = CRUDError(
            code="VALIDATION_ERROR",
            message_key="validation.min_length",
            field="name",
            params={"min_length": 3},
        )
        return CRUDResult(success=False, data=None, errors=[error])

    endpoint = Endpoint(path="/api/v1/plants", method="POST", handler=handler)
    registry.register("POST", "/api/v1/plants", endpoint)

    @app.post("/api/v1/plants")
    async def plants(request: Request):
        body = await request.json()
        http_request = {
            "query": dict(request.query_params),
            "body": body,
            "headers": dict(request.headers),
            "path_params": {},
        }
        result = adapter.handle_request("POST", "/api/v1/plants", http_request)
        return JSONResponse(content=result["json"], status_code=result["status"])

    client = TestClient(app)
    response = client.post("/api/v1/plants", json={"name": ""})
    assert response.status_code == 422
    assert response.json()["success"] is False


def test_get_not_found_404(setup_app):
    app, registry, adapter = setup_app

    def handler(request):
        error = CRUDError(
            code="NOT_FOUND", message_key="entity.not_found", field="id", params={}
        )
        return CRUDResult(success=False, data=None, errors=[error])

    endpoint = Endpoint(path="/api/v1/plants/{id}", method="GET", handler=handler)
    registry.register("GET", "/api/v1/plants/{id}", endpoint)

    @app.get("/api/v1/plants/{id}")
    async def plants(id: str, request: Request):
        http_request = {
            "query": dict(request.query_params),
            "body": {},
            "headers": dict(request.headers),
            "path_params": {"id": id},
        }
        result = adapter.handle_request("GET", f"/api/v1/plants/{id}", http_request)
        return JSONResponse(content=result["json"], status_code=result["status"])

    client = TestClient(app)
    response = client.get("/api/v1/plants/999")
    assert response.status_code == 404
    assert response.json()["success"] is False


def test_get_persistence_error_500(setup_app):
    app, registry, adapter = setup_app

    def handler(request):
        error = CRUDError(
            code="PERSISTENCE_ERROR", message_key="db.failure", field=None, params={}
        )
        return CRUDResult(success=False, data=None, errors=[error])

    endpoint = Endpoint(path="/api/v1/plants", method="GET", handler=handler)
    registry.register("GET", "/api/v1/plants", endpoint)

    @app.get("/api/v1/plants")
    async def plants(request: Request):
        http_request = {
            "query": dict(request.query_params),
            "body": {},
            "headers": dict(request.headers),
            "path_params": {},
        }
        result = adapter.handle_request("GET", "/api/v1/plants", http_request)
        return JSONResponse(content=result["json"], status_code=result["status"])

    client = TestClient(app)
    response = client.get("/api/v1/plants")
    assert response.status_code == 500
    assert response.json()["success"] is False
