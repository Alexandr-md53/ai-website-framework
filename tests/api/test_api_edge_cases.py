import pytest
from ai_framework.api.registry import EndpointRegistry
from ai_framework.api.endpoint import Endpoint
from ai_framework.api.router import Router
from ai_framework.api.adapter import APIAdapter
from ai_framework.crud.contracts import CRUDResult


def sample_handler(request):
    return CRUDResult(
        success=True,
        data={"item_id": request.get("id", 1)},
        errors=[],
        operation="read",
    )


@pytest.fixture
def api_setup():
    registry = EndpointRegistry()
    # Регистрируем ТОЛЬКО GET для /api/v1/plants и GET для /api/v1/plants/{id}
    endpoint_list = Endpoint(
        path="/api/v1/plants", method="GET", handler=sample_handler
    )
    endpoint_detail = Endpoint(
        path="/api/v1/plants/{id}", method="GET", handler=sample_handler
    )

    registry.register("GET", "/api/v1/plants", endpoint_list)
    registry.register("GET", "/api/v1/plants/{id}", endpoint_detail)

    router = Router(registry)
    adapter = APIAdapter(router)
    return adapter, registry, router


# ----------------------------------------------------------------------
# 1. Кейс: 404 Unknown Route (Маршрут вообще не зарегистрирован)
# ----------------------------------------------------------------------
def test_unknown_route_returns_404(api_setup):
    adapter, _, _ = api_setup
    http_request = {"query": {}, "body": {}, "headers": {}, "path_params": {}}

    result = adapter.handle_request(
        "GET", "/api/v1/non_existent_endpoint", http_request
    )

    assert result["status"] == 404
    assert result["json"]["success"] is False
    assert any(
        err.get("code") == "NOT_FOUND" for err in result["json"].get("errors", [])
    )


# ----------------------------------------------------------------------
# 2. Кейс: 405 Method Not Allowed (Путь есть, но метод POST не зарегистрирован)
# ----------------------------------------------------------------------
def test_method_not_allowed_returns_405(api_setup):
    adapter, _, _ = api_setup
    http_request = {
        "query": {},
        "body": {"name": "ficus"},
        "headers": {},
        "path_params": {},
    }

    # Путь /api/v1/plants существует, но под микроскопом только GET
    result = adapter.handle_request("POST", "/api/v1/plants", http_request)

    assert result["status"] == 405
    assert result["json"]["success"] is False
    assert any(
        err.get("code") == "METHOD_NOT_ALLOWED"
        for err in result["json"].get("errors", [])
    )


# ----------------------------------------------------------------------
# 3. Кейс: 400 Bad Request (Битый / некорректный JSON в body)
# ----------------------------------------------------------------------
def test_malformed_json_body_returns_400(api_setup):
    adapter, _, _ = api_setup
    # Передаем строковый "мусор" вместо нормального словаря/JSON
    http_request = {
        "query": {},
        "body": "INVALID_JSON_{{",
        "headers": {},
        "path_params": {},
    }

    result = adapter.handle_request("GET", "/api/v1/plants", http_request)

    assert result["status"] == 400
    assert result["json"]["success"] is False
    assert any(
        err.get("code") == "BAD_REQUEST" for err in result["json"].get("errors", [])
    )


# ----------------------------------------------------------------------
# 4. Кейс: Обработка middleware (сквозной перехват ошибок / заголовков)
# ----------------------------------------------------------------------
def test_middleware_execution_chain(api_setup):
    adapter, _, router = api_setup

    # Симулируем работу middleware, модифицирующего контекст
    executed = []

    def dummy_middleware(request, next_fn):
        executed.append("before")
        response = next_fn(request)
        executed.append("after")
        return response

    if hasattr(router, "use_middleware"):
        router.use_middleware(dummy_middleware)
        http_request = {"query": {}, "body": {}, "headers": {}, "path_params": {}}
        adapter.handle_request("GET", "/api/v1/plants", http_request)
        assert executed == ["before", "after"]
    else:
        pytest.fail("Router does not implement use_middleware method")
