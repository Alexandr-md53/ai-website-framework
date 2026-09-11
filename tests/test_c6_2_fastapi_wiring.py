# CODING: utf-8, ASCII only
from fastapi.testclient import TestClient
from ai_framework.api.registry import EndpointRegistry
from ai_framework.api.endpoint import Endpoint
from ai_framework.api.contracts import CRUDResult
from ai_framework.api.fastapi import create_app


def test_middlewares_via_router():
    registry = EndpointRegistry()

    def handler(request):
        return CRUDResult(
            success=True, data={"via_mw": request.get("via_mw")}, errors=[]
        )

    ep = Endpoint(path="/api/v1/plants", method="GET", handler=handler)
    registry.register("GET", "/api/v1/plants", ep)

    def test_mw(req, next_fn):
        req["via_mw"] = True
        return next_fn(req)

    app = create_app(registry, middlewares=[test_mw])
    client = TestClient(app)
    r = client.get("/api/v1/plants")
    assert r.status_code == 200
    assert r.json()["data"]["via_mw"] is True


def test_health_included_by_default():
    registry = EndpointRegistry()
    app = create_app(registry, include_health=True)
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert "version" in r.json()


def test_health_excluded():
    registry = EndpointRegistry()
    app = create_app(registry, include_health=False)
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 404


def test_lifespan_passthrough():
    from contextlib import asynccontextmanager

    state = {"started": False}

    @asynccontextmanager
    async def lifespan(app):
        state["started"] = True
        yield
        state["started"] = False

    registry = EndpointRegistry()
    app = create_app(registry, lifespan=lifespan, include_health=False)
    with TestClient(app) as client:
        assert state["started"] is True
        r = client.get("/nonexistent")
        assert r.status_code == 404
    assert state["started"] is False


def test_c61_still_works():
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
