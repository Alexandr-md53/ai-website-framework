from fastapi.testclient import TestClient
from ai_framework.api.registry import EndpointRegistry
from ai_framework.api.endpoint import Endpoint
from ai_framework.api.contracts import CRUDResult
from ai_framework.api.fastapi import create_app


def test_create_app_factory():
    registry = EndpointRegistry()

    def handler(request):
        return CRUDResult(success=True, data={"id": 1}, errors=[])

    ep = Endpoint(path="/api/v1/plants", method="GET", handler=handler)
    registry.register("GET", "/api/v1/plants", ep)

    app = create_app(registry)
    client = TestClient(app)
    r = client.get("/api/v1/plants")
    assert r.status_code == 200
    assert r.json()["data"]["id"] == 1


def test_create_app_empty():
    from ai_framework.api.fastapi import create_app

    app = create_app()
    assert app is not None
