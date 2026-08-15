import inspect

from ai_framework.crud.contracts import (
    CRUDContext,
    CRUDError,
    CRUDResult,
    PersistenceProviderProtocol,
    UniversalCRUDEngineProtocol,
)


def test_crud_context_defaults():
    context = CRUDContext()

    assert context.tenant_id is None
    assert context.locale == "en"


def test_crud_context_custom_values():
    context = CRUDContext(
        tenant_id="tenant-1",
        locale="ru",
    )

    assert context.tenant_id == "tenant-1"
    assert context.locale == "ru"


def test_crud_context_is_frozen():
    context = CRUDContext()

    try:
        context.locale = "ru"
        assert False, "CRUDContext should be immutable"
    except AttributeError:
        pass


def test_crud_error_defaults():
    error = CRUDError(
        code="NOT_FOUND",
        message_key="crud.not_found",
    )

    assert error.code == "NOT_FOUND"
    assert error.message_key == "crud.not_found"
    assert error.field is None
    assert error.params == {}


def test_crud_error_with_field_and_params():
    error = CRUDError(
        code="VALIDATION_ERROR",
        message_key="validation.required",
        field="name",
        params={"field": "name"},
    )

    assert error.code == "VALIDATION_ERROR"
    assert error.message_key == "validation.required"
    assert error.field == "name"
    assert error.params == {"field": "name"}


def test_crud_result_success():
    data = {"id": 1, "name": "Rose"}

    result = CRUDResult(
        success=True,
        data=data,
    )

    assert result.success is True
    assert result.data == data
    assert result.errors == []


def test_crud_result_failure():
    error = CRUDError(
        code="NOT_FOUND",
        message_key="crud.not_found",
    )

    result = CRUDResult(
        success=False,
        errors=[error],
    )

    assert result.success is False
    assert result.data is None
    assert result.errors == [error]


def test_crud_result_list_data():
    data = [
        {"id": 1, "name": "Rose"},
        {"id": 2, "name": "Tulip"},
    ]

    result = CRUDResult(
        success=True,
        data=data,
    )

    assert result.success is True
    assert result.data == data


def test_crud_dataclasses_are_frozen():
    context = CRUDContext()
    error = CRUDError(
        code="TEST",
        message_key="test.message",
    )
    result = CRUDResult(success=True)

    for obj, attribute, value in [
        (context, "locale", "ru"),
        (error, "code", "OTHER"),
        (result, "success", False),
    ]:
        try:
            setattr(obj, attribute, value)
            assert False, f"{type(obj).__name__} should be immutable"
        except AttributeError:
            pass


def test_persistence_provider_protocol_methods():
    expected_methods = {
        "insert",
        "fetch",
        "fetch_all",
        "update_record",
        "delete_record",
        "is_unique",
    }

    actual_methods = {
        name
        for name, member in inspect.getmembers(
            PersistenceProviderProtocol,
            predicate=inspect.isfunction,
        )
        if not name.startswith("_")
    }

    assert expected_methods.issubset(actual_methods)


def test_crud_engine_protocol_methods():
    expected_methods = {
        "create",
        "get",
        "list",
        "update",
        "delete",
    }

    actual_methods = {
        name
        for name, member in inspect.getmembers(
            UniversalCRUDEngineProtocol,
            predicate=inspect.isfunction,
        )
        if not name.startswith("_")
    }

    assert expected_methods.issubset(actual_methods)


def test_crud_engine_protocol_methods_are_async():
    for method_name in (
        "create",
        "get",
        "list",
        "update",
        "delete",
    ):
        method = getattr(UniversalCRUDEngineProtocol, method_name)

        assert inspect.iscoroutinefunction(method), f"{method_name} must be async"


def test_persistence_protocol_methods_are_async():
    for method_name in (
        "insert",
        "fetch",
        "fetch_all",
        "update_record",
        "delete_record",
        "is_unique",
    ):
        method = getattr(PersistenceProviderProtocol, method_name)

        assert inspect.iscoroutinefunction(method), f"{method_name} must be async"
