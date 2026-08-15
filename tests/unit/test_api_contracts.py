import pytest
from ai_framework.api.contracts import (
    APIResponse,
    CRUDResult,
    map_crud_result_to_http_status,
)
from ai_framework.api.adapter import ResponseAdapter
from ai_framework.crud.contracts import CRUDError


@pytest.mark.parametrize(
    "success, operation, errors, expected_status",
    [
        (True, "create", [], 201),
        (True, "get", [], 200),
        (True, "list", [], 200),
        (True, "update", [], 200),
        (True, "delete", [], 200),
        (False, "get", [CRUDError(code="VALIDATION_ERROR", message_key="v.err")], 422),
        (False, "get", [CRUDError(code="NOT_FOUND", message_key="n.err")], 404),
        (False, "get", [CRUDError(code="PERSISTENCE_ERROR", message_key="p.err")], 500),
        (False, "get", [CRUDError(code="BAD_REQUEST", message_key="b.err")], 400),
        (False, "get", [CRUDError(code="UNKNOWN_CODE", message_key="u.err")], 400),
    ],
)
def test_map_crud_result_to_http_status_matrix(
    success, operation, errors, expected_status
):
    result = CRUDResult(success=success, operation=operation, data=None, errors=errors)
    assert map_crud_result_to_http_status(result) == expected_status


def test_api_response_from_crud_result_preservation():
    error = CRUDError(
        code="VALIDATION_ERROR",
        message_key="validation.required",
        field="name",
        params={"key": "val"},
    )
    crud_result = CRUDResult(
        success=False, operation="create", data=None, errors=[error]
    )

    response = APIResponse.from_crud_result(crud_result)

    assert isinstance(response, APIResponse)
    assert response.success is False
    assert response.data is None
    assert response.operation == "create"
    assert len(response.errors) == 1
    assert response.errors[0]["code"] == "VALIDATION_ERROR"
    assert response.errors[0]["field"] == "name"


def test_response_adapter_build_serialization():
    error = CRUDError(code="NOT_FOUND", message_key="crud.not_found", field="id")
    response = APIResponse(
        success=False,
        operation="get",
        data=None,
        errors=[
            {
                "code": error.code,
                "message_key": error.message_key,
                "field": error.field,
                "params": error.params,
            }
        ],
    )

    built_data = ResponseAdapter.build(response)

    # Проверяем структуру верхнего уровня
    assert built_data["success"] is False
    assert built_data["data"] is None
    assert isinstance(built_data["errors"], list)

    # Проверка сериализации вложенных ошибок в словари
    serialized_error = built_data["errors"][0]
    assert isinstance(serialized_error, dict)
    assert serialized_error["code"] == "NOT_FOUND"
    assert serialized_error["message_key"] == "crud.not_found"
    assert serialized_error["field"] == "id"
