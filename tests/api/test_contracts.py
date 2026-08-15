import pytest
from ai_framework.api.contracts import APIResponse
from ai_framework.crud.contracts import CRUDError


def test_cruderror_to_dict():
    error = CRUDError(
        code="VALIDATION_ERROR",
        message_key="validation.min_length",
        field="name",
        params={"min_length": 3},
    )
    result = error.to_dict()
    assert result == {
        "code": "VALIDATION_ERROR",
        "message_key": "validation.min_length",
        "field": "name",
        "params": {"min_length": 3},
    }


def test_apiresponse_to_dict_without_errors():
    response = APIResponse(success=True, data={"id": 1}, errors=[])
    result = response.to_dict()
    assert result == {
        "success": True,
        "data": {"id": 1},
        "errors": [],
    }


def test_apiresponse_to_dict_with_one_error():
    error = CRUDError(
        code="NOT_FOUND",
        message_key="entity.not_found",
        field="user_id",
        params={},
    )
    response = APIResponse(success=False, data=None, errors=[error])
    result = response.to_dict()
    assert result == {
        "success": False,
        "data": None,
        "errors": [
            {
                "code": "NOT_FOUND",
                "message_key": "entity.not_found",
                "field": "user_id",
                "params": {},
            }
        ],
    }


def test_apiresponse_to_dict_with_multiple_errors():
    errors = [
        CRUDError(
            code="VALIDATION_ERROR",
            message_key="validation.min_length",
            field="name",
            params={"min_length": 3},
        ),
        CRUDError(
            code="BAD_REQUEST", message_key="request.invalid", field=None, params={}
        ),
    ]
    response = APIResponse(success=False, data=None, errors=errors)
    result = response.to_dict()
    assert result["success"] is False
    assert result["data"] is None
    assert len(result["errors"]) == 2


def test_apiresponse_to_dict_data_none():
    response = APIResponse(success=True, data=None, errors=[])
    result = response.to_dict()
    assert result == {
        "success": True,
        "data": None,
        "errors": [],
    }


def test_cruderror_to_dict_with_empty_params_and_field_none():
    error = CRUDError(
        code="BAD_REQUEST", message_key="request.invalid", field=None, params={}
    )
    result = error.to_dict()
    assert result == {
        "code": "BAD_REQUEST",
        "message_key": "request.invalid",
        "field": None,
        "params": {},
    }


def test_apiresponse_to_dict_with_empty_errors_and_none_data():
    response = APIResponse(success=False, data=None, errors=[])
    result = response.to_dict()
    assert result == {
        "success": False,
        "data": None,
        "errors": [],
    }


def test_apiresponse_to_dict_with_multiple_errors_and_none_field():
    errors = [
        CRUDError(
            code="VALIDATION_ERROR",
            message_key="validation.min_length",
            field="name",
            params={"min_length": 3},
        ),
        CRUDError(
            code="BAD_REQUEST", message_key="request.invalid", field=None, params={}
        ),
    ]
    response = APIResponse(success=False, data={"foo": "bar"}, errors=errors)
    result = response.to_dict()
    assert result["success"] is False
    assert result["data"] == {"foo": "bar"}
    assert result["errors"][0]["field"] == "name"
    assert result["errors"][1]["field"] is None
