# CODING: utf-8, ASCII only
"""
C10.1 contract — Product Assembly Factory
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any
from fastapi.testclient import TestClient

from ai_framework.product_registry import ProductInfo

@dataclass(frozen=True)
class DummyDTO:
    title: str

class DummyUseCase:
    def __init__(self):
        self.calls = []

    def execute(self, dto: DummyDTO):
        self.calls.append(dto)
        return {"ok": True, "title": dto.title}

def _dto_factory(api_req: Dict[str, Any]) -> DummyDTO:
    body = api_req.get("body", {})
    return DummyDTO(title=body.get("title", ""))

def _make_product_info():
    return ProductInfo(
        name="test-product",
        path=Path("/tmp/test-product"),
        manifest={"version": "0.1.0", "description": "test product for C10.1"},
    )

def test_c10_1_factory_function_must_exist():
    from ai_framework.product.factory import build_app_from_product_info
    assert callable(build_app_from_product_info)

def test_c10_1_factory_accepts_product_info_metadata():
    from ai_framework.product.factory import build_app_from_product_info
    info = _make_product_info()
    uc = DummyUseCase()
    app = build_app_from_product_info(info, {("POST", "/test"): (uc, _dto_factory)})
    assert app is not None

def test_c10_1_factory_does_not_scan_filesystem():
    from ai_framework.product import factory as factory_module
    import inspect
    src = inspect.getsource(factory_module)
    forbidden = ["os.listdir", "os.walk", "glob", "pathlib", "rglob", "iterdir", "scandir"]
    for token in forbidden:
        # allow import of Path for ProductInfo usage, but not scanning calls
        if token == "pathlib" and "from pathlib import" in src:
            continue
        assert token not in src.lower() or token == "pathlib", f"Factory must not scan FS: {token}"

def test_c10_1_factory_uses_c9_2_builder_and_c6_create_app():
    from ai_framework.product import factory as factory_module
    import inspect
    src = inspect.getsource(factory_module)
    assert "build_registry_from_map" in src, "Must use C9.2 builder"
    assert "create_app" in src, "Must use C6 create_app"

def test_c10_1_factory_produces_working_fastapi_app():
    from ai_framework.product.factory import build_app_from_product_info
    info = _make_product_info()
    uc = DummyUseCase()
    app = build_app_from_product_info(info, {("POST", "/test"): (uc, _dto_factory)})
    client = TestClient(app)
    resp = client.post("/test", json={"title": "hello"})
    assert resp.status_code == 200
    payload = resp.json().get("json", resp.json())
    assert payload.get("title") == "hello" or payload.get("ok") is True
    assert len(uc.calls) == 1
    assert uc.calls[0].title == "hello"

def test_c10_1_factory_does_not_create_alternative_registry():
    from ai_framework.product import factory as factory_module
    import inspect
    src = inspect.getsource(factory_module)
    assert "class ProductRegistry" not in src
    assert "class EndpointRegistry" not in src