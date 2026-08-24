from unittest.mock import MagicMock
from ai_framework.crud_ui.web import CrudWebController, HTTPRequestContext


def test_web_integration_list_flow():
    engine = MagicMock()
    engine.get_list_context.return_value = {"items": [{"id": "1", "title": "Item 1"}]}
    controller = CrudWebController(engine=engine)

    # 1. Direct call
    assert controller.handle_list() == {"items": [{"id": "1", "title": "Item 1"}]}

    # 2. Dispatch call
    context = HTTPRequestContext(method="GET", path="/items/")
    assert controller.dispatch(context) == {"items": [{"id": "1", "title": "Item 1"}]}


def test_web_integration_detail_flow():
    engine = MagicMock()
    engine.get_detail_context.return_value = {
        "item": {"id": "42", "title": "Detail Item"}
    }
    controller = CrudWebController(engine=engine)

    # 1. Direct call
    assert controller.handle_detail("42") == {
        "item": {"id": "42", "title": "Detail Item"}
    }

    # 2. Dispatch call
    context = HTTPRequestContext(method="GET", path="/items/42/detail")
    assert controller.dispatch(context) == {
        "item": {"id": "42", "title": "Detail Item"}
    }


def test_web_integration_create_get_flow():
    engine = MagicMock()
    engine.get_create_form_context.return_value = {"fields": ["title", "content"]}
    controller = CrudWebController(engine=engine)

    # 1. Direct call
    assert controller.handle_create_get() == {"fields": ["title", "content"]}

    # 2. Dispatch call
    context = HTTPRequestContext(method="GET", path="/items/create")
    assert controller.dispatch(context) == {"fields": ["title", "content"]}


def test_web_integration_create_post_flow():
    engine = MagicMock()
    engine.crud_service.create.return_value = {"id": "100", "title": "New Post"}
    controller = CrudWebController(engine=engine)

    # 1. Direct call
    result = controller.handle_create_post({"title": "New Post"})
    engine.crud_service.create.assert_called_with({"title": "New Post"})
    assert result == {"id": "100", "title": "New Post"}

    # 2. Dispatch call
    context = HTTPRequestContext(
        method="POST", path="/items/create", form_data={"title": "New Post"}
    )
    dispatch_result = controller.dispatch(context)
    assert dispatch_result == {"id": "100", "title": "New Post"}


def test_web_integration_edit_get_flow():
    engine = MagicMock()
    engine.get_edit_form_context.return_value = {
        "item": {"id": "42", "title": "Existing"}
    }
    controller = CrudWebController(engine=engine)

    # 1. Direct call
    assert controller.handle_edit_get("42") == {
        "item": {"id": "42", "title": "Existing"}
    }

    # 2. Dispatch call
    context = HTTPRequestContext(method="GET", path="/items/42/edit")
    assert controller.dispatch(context) == {"item": {"id": "42", "title": "Existing"}}


def test_web_integration_edit_post_flow():
    engine = MagicMock()
    engine.crud_service.get.return_value = {
        "id": "42",
        "title": "Old Title",
        "category": "General",
    }
    engine.crud_service.update.return_value = {
        "id": "42",
        "title": "Updated Title",
        "category": "General",
    }
    controller = CrudWebController(engine=engine)

    # 1. Direct call
    result = controller.handle_edit_post("42", {"title": "Updated Title"})
    engine.crud_service.update.assert_called_with(
        "42", {"title": "Updated Title", "category": "General"}
    )
    assert result == {"id": "42", "title": "Updated Title", "category": "General"}

    # 2. Dispatch call
    context = HTTPRequestContext(
        method="POST", path="/items/42/edit", form_data={"title": "Updated Title"}
    )
    dispatch_result = controller.dispatch(context)
    assert dispatch_result == {
        "id": "42",
        "title": "Updated Title",
        "category": "General",
    }
