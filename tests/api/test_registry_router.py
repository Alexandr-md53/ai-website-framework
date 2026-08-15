import pytest

from ai_framework.api.endpoint import Endpoint
from ai_framework.api.registry import EndpointRegistry
from ai_framework.api.router import Router


def dummy_handler(request):
    return {"ok": True, "request": request}


def test_registry_register_and_get():
    registry = EndpointRegistry()
    endpoint = Endpoint(path="/api/v1/plants", method="GET", handler=dummy_handler)
    registry.register("GET", "/api/v1/plants", endpoint)
    result = registry.get("GET", "/api/v1/plants")
    assert result is endpoint


def test_registry_list():
    registry = EndpointRegistry()
    endpoint = Endpoint(path="/api/v1/plants", method="GET", handler=dummy_handler)
    registry.register("GET", "/api/v1/plants", endpoint)
    assert ("GET", "/api/v1/plants") in registry.list()


def test_registry_get_missing():
    registry = EndpointRegistry()
    assert registry.get("GET", "/missing") is None


def test_endpoint_handle_calls_handler():
    endpoint = Endpoint(path="/api/v1/plants", method="GET", handler=dummy_handler)
    result = endpoint.handle({"foo": "bar"})
    assert result["ok"] is True
    assert result["request"] == {"foo": "bar"}


def test_router_finds_endpoint_and_calls_handler():
    registry = EndpointRegistry()
    endpoint = Endpoint(path="/api/v1/plants", method="GET", handler=dummy_handler)
    registry.register("GET", "/api/v1/plants", endpoint)
    router = Router(registry)
    result = router.route("GET", "/api/v1/plants", {"foo": "bar"})
    assert result["ok"] is True


def test_router_extracts_path_parameter():
    def handler(request):
        return {"id": request["id"]}

    registry = EndpointRegistry()
    endpoint = Endpoint(path="/api/v1/plants/{id}", method="GET", handler=handler)
    registry.register("GET", "/api/v1/plants/{id}", endpoint)
    router = Router(registry)
    result = router.route("GET", "/api/v1/plants/42", {})
    assert result["id"] == "42"


def test_router_missing_endpoint():
    registry = EndpointRegistry()
    router = Router(registry)
    with pytest.raises(KeyError):
        router.route("GET", "/not-found", {})
