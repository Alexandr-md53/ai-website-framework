import pytest

from ai_framework.api.adapter import RequestAdapter, ResponseAdapter, APIAdapter
from ai_framework.api.endpoint import Endpoint
from ai_framework.api.registry import EndpointRegistry
from ai_framework.api.router import Router
from ai_framework.api.contracts import CRUDError, CRUDResult, APIResponse


def test_request_adapter_builds_dict():
    http_request = {
        "query": {"q": "lavender"},
        "body": {"name": "plant"},
        "headers": {"Authorization": "Bearer token"},
        "path_params": {"id": "42"},
    }
    adapter = RequestAdapter(http_request)
    result = adapter.to_dict()
    assert result["query"]["q"] == "lavender"
    assert result["body"]["name"] == "plant"
    assert result["path_params"]["id"] == "42"


def test_response_adapter_builds_http_response():
    crud_result = CRUDResult(success=True, data={"id": 1}, errors=[])
    api_response = APIResponse.from_crud_result(crud_result)
    status, response = api_response
    adapted = ResponseAdapter.build(status, response)
    assert adapted["status"] == 200
    assert adapted["json"]["success"] is True
    assert adapted["json"]["data"]["id"] == 1


def test_api_adapter_handle_request_success_get():
    def handler(request):
        return CRUDResult(success=True, data={"id": 1}, errors=[])

    registry = EndpointRegistry()
    endpoint = Endpoint(path="/api/v1/plants", method="GET", handler=handler)
    registry.register("GET", "/api/v1/plants", endpoint)
    router = Router(registry)
    adapter = APIAdapter(router)

    http_request = {"query": {}, "body": {}, "headers": {}, "path_params": {}}
    result = adapter.handle_request("GET", "/api/v1/plants", http_request)
    assert result["status"] == 200
    assert result["json"]["data"]["id"] == 1


def test_api_adapter_handle_request_success_post():
    def handler(request):
        return CRUDResult(success=True, data={"id": 99}, errors=[])

    registry = EndpointRegistry()
    endpoint = Endpoint(path="/api/v1/plants", method="POST", handler=handler)
    registry.register("POST", "/api/v1/plants", endpoint)
    router = Router(registry)
    adapter = APIAdapter(router)

    http_request = {
        "query": {},
        "body": {"name": "rose"},
        "headers": {},
        "path_params": {},
    }
    result = adapter.handle_request("POST", "/api/v1/plants", http_request)
    assert result["status"] == 200
    assert result["json"]["data"]["id"] == 99


def test_api_adapter_handle_request_validation_error():
    def handler(request):
        error = CRUDError(
            code="VALIDATION_ERROR",
            message_key="validation.min_length",
            field="name",
            params={"min_length": 3},
        )
        return CRUDResult(success=False, data=None, errors=[error])

    registry = EndpointRegistry()
    endpoint = Endpoint(path="/api/v1/plants", method="POST", handler=handler)
    registry.register("POST", "/api/v1/plants", endpoint)
    router = Router(registry)
    adapter = APIAdapter(router)

    http_request = {"query": {}, "body": {"name": ""}, "headers": {}, "path_params": {}}
    result = adapter.handle_request("POST", "/api/v1/plants", http_request)
    assert result["status"] == 422
    assert result["json"]["success"] is False


def test_api_adapter_handle_request_not_found():
    def handler(request):
        error = CRUDError(
            code="NOT_FOUND", message_key="entity.not_found", field="id", params={}
        )
        return CRUDResult(success=False, data=None, errors=[error])

    registry = EndpointRegistry()
    endpoint = Endpoint(path="/api/v1/plants/{id}", method="GET", handler=handler)
    registry.register("GET", "/api/v1/plants/{id}", endpoint)
    router = Router(registry)
    adapter = APIAdapter(router)

    http_request = {"query": {}, "body": {}, "headers": {}, "path_params": {}}
    result = adapter.handle_request("GET", "/api/v1/plants/999", http_request)
    assert result["status"] == 404
    assert result["json"]["success"] is False


def test_api_adapter_handle_request_persistence_error():
    def handler(request):
        error = CRUDError(
            code="PERSISTENCE_ERROR", message_key="db.failure", field=None, params={}
        )
        return CRUDResult(success=False, data=None, errors=[error])

    registry = EndpointRegistry()
    endpoint = Endpoint(path="/api/v1/plants", method="GET", handler=handler)
    registry.register("GET", "/api/v1/plants", endpoint)
    router = Router(registry)
    adapter = APIAdapter(router)

    http_request = {"query": {}, "body": {}, "headers": {}, "path_params": {}}
    result = adapter.handle_request("GET", "/api/v1/plants", http_request)
    assert result["status"] == 500
    assert result["json"]["success"] is False
