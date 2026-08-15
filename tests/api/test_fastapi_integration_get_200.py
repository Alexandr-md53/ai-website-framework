import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from ai_framework.api.registry import EndpointRegistry
from ai_framework.api.router import Router
from ai_framework.api.adapter import APIAdapter
from ai_framework.api.contracts import CRUDResult


def test_fastapi_integration_get_200():
    # создаём FastAPI приложение
    app = FastAPI()
    registry = EndpointRegistry()
    router = Router(registry)
    adapter = APIAdapter(router)

    # mock handler возвращает CRUDResult
    def handler(request):
        return CRUDResult(success=True, data={"id": 1}, errors=[], operation="create")

    # регистрируем endpoint
    from ai_framework.api.endpoint import Endpoint

    endpoint = Endpoint(path="/api/v1/plants", method="GET", handler=handler)
    registry.register("GET", "/api/v1/plants", endpoint)

    # FastAPI route → APIAdapter
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
