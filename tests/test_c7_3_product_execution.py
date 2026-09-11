# CODING: utf-8, ASCII only
"""
C7.3 Product Execution Boundary Freeze — contract tests only

Path B: Product/Showcase → UniversalCRUDEngine (direct, no use-case layer)
vs Path A: DTO → UseCase → Repository → CRUDArticleRepository → UniversalCRUDEngine (C7.2)

Freezes:
- CRUDContext / CRUDResult / CRUDError
- PersistenceProviderProtocol
- UniversalCRUDEngineProtocol
- UniversalCRUDEngine (new engine)
- CRUDEngine legacy facade (backward compat)
"""

import inspect
import pytest

from ai_framework.crud.contracts import (
    CRUDContext,
    CRUDResult,
    CRUDError,
    PersistenceProviderProtocol,
    UniversalCRUDEngineProtocol,
)
from ai_framework.crud.engine import UniversalCRUDEngine
from ai_framework.crud.crud_engine import CRUDEngine

# ---- Fakes for persistence ----


class FakePersistence:
    def __init__(self):
        self.store = {}
        self._seq = 0

    async def insert(self, entity_name, data):
        self._seq += 1
        rec = dict(data)
        rec.setdefault("id", str(self._seq))
        self.store[rec["id"]] = rec
        return rec

    async def fetch(self, entity_name, entity_id):
        return self.store.get(str(entity_id))

    async def fetch_all(self, entity_name, filters=None):
        vals = list(self.store.values())
        if not filters:
            return vals
        # minimal filter: exact match on top-level keys
        return [r for r in vals if all(r.get(k) == v for k, v in filters.items())]

    async def update_record(self, entity_name, entity_id, data):
        eid = str(entity_id)
        if eid not in self.store:
            return None
        self.store[eid].update(data)
        return self.store[eid]

    async def delete_record(self, entity_name, entity_id):
        return self.store.pop(str(entity_id), None) is not None

    async def is_unique(self, entity_name, field_name, value, exclude_id=None):
        for rid, rec in self.store.items():
            if exclude_id is not None and str(rid) == str(exclude_id):
                continue
            if rec.get(field_name) == value:
                return False
        return True


class FakeValidationEngine:
    def __init__(self, valid=True):
        self._valid = valid
        self.called_with = None

    async def validate_entity(self, entity_name, payload):
        self.called_with = (entity_name, payload)

        class Res:
            def __init__(self, valid):
                self.valid = valid
                self.errors = []

        return Res(self._valid)


class FakeSlugOrchestrator:
    def __init__(self):
        self.called = False

    async def process(self, entity_name, payload, context=None):
        self.called = True
        p = dict(payload)
        if "title" in p and "slug" not in p:
            p["slug"] = p["title"].lower().replace(" ", "-")
        return p


# ---- Contract existence ----


def test_crud_context_metadata():
    ctx = CRUDContext(tenant_id="t1", locale="en")
    assert ctx.tenant_id == "t1"
    assert ctx.locale == "en"
    ctx2 = CRUDContext()
    assert ctx2.tenant_id is None
    assert ctx2.locale == "en"


def test_crud_error_to_dict():
    err = CRUDError(
        code="NOT_FOUND", message_key="not found", field="id", params={"id": 1}
    )
    d = err.to_dict()
    assert d["code"] == "NOT_FOUND"
    assert d["message_key"] == "not found"
    assert d["field"] == "id"
    assert d["params"]["id"] == 1


def test_crud_result_fields():
    r = CRUDResult(success=True, data={"id": "1"}, errors=[], operation="create")
    assert r.success is True
    assert r.data["id"] == "1"
    assert r.operation == "create"
    # default operation is "read"
    r2 = CRUDResult(success=False, data=None, errors=[])
    assert r2.operation == "read"


def test_persistence_provider_protocol_runtime_checkable():
    fake = FakePersistence()
    assert isinstance(fake, PersistenceProviderProtocol)
    # check required methods exist
    for m in [
        "insert",
        "fetch",
        "fetch_all",
        "update_record",
        "delete_record",
        "is_unique",
    ]:
        assert hasattr(fake, m)
        assert callable(getattr(fake, m))


def test_universal_engine_protocol_runtime_checkable():
    persistence = FakePersistence()
    engine = UniversalCRUDEngine(persistence_provider=persistence)
    assert isinstance(engine, UniversalCRUDEngineProtocol)
    for m in ["create", "get", "list", "update", "delete"]:
        assert hasattr(engine, m)
        assert inspect.iscoroutinefunction(getattr(engine, m))


def test_legacy_crud_engine_exists_for_backward_compat():
    # CRUDEngine legacy facade must be importable (backward compat for slug integration tests)
    assert CRUDEngine is not None
    # also aliased in engine.py as fallback
    from ai_framework.crud.engine import CRUDEngine as Aliased

    assert Aliased is not None


# ---- UniversalCRUDEngine execution contract ----


@pytest.mark.asyncio
async def test_universal_engine_create_success():
    persistence = FakePersistence()
    engine = UniversalCRUDEngine(persistence_provider=persistence)
    res = await engine.create("article", {"title": "Hello"}, context=CRUDContext())
    assert isinstance(res, CRUDResult)
    assert res.success is True
    assert res.data["title"] == "Hello"
    assert "id" in res.data


@pytest.mark.asyncio
async def test_universal_engine_create_with_validation_and_slug():
    persistence = FakePersistence()
    validation = FakeValidationEngine(valid=True)
    slug_orch = FakeSlugOrchestrator()
    engine = UniversalCRUDEngine(
        persistence_provider=persistence,
        validation_engine=validation,
        slug_orchestrator=slug_orch,
    )
    res = await engine.create("post", {"title": "My Title"}, context=CRUDContext())
    assert res.success is True
    assert validation.called_with is not None
    assert slug_orch.called is True
    assert res.data["slug"] == "my-title"


@pytest.mark.asyncio
async def test_universal_engine_create_validation_failure():
    persistence = FakePersistence()
    validation = FakeValidationEngine(valid=False)
    engine = UniversalCRUDEngine(
        persistence_provider=persistence, validation_engine=validation
    )

    # validation engine returning invalid must produce failure CRUDResult
    # need to simulate errors attribute
    class BadValidationEngine:
        async def validate_entity(self, en, payload):
            class E:
                code = "REQUIRED"
                message_key = "required"
                field = "title"
                params = {}

            class Res:
                valid = False
                errors = [E()]

            return Res()

    engine2 = UniversalCRUDEngine(
        persistence_provider=persistence, validation_engine=BadValidationEngine()
    )
    res = await engine2.create("article", {}, context=CRUDContext())
    assert res.success is False
    assert len(res.errors) == 1
    assert isinstance(res.errors[0], CRUDError)
    assert res.errors[0].code == "REQUIRED"


@pytest.mark.asyncio
async def test_universal_engine_get_not_found():
    persistence = FakePersistence()
    engine = UniversalCRUDEngine(persistence_provider=persistence)
    res = await engine.get("article", "missing-id")
    assert res.success is False
    assert res.data is None
    assert res.errors[0].code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_universal_engine_crud_cycle():
    persistence = FakePersistence()
    engine = UniversalCRUDEngine(persistence_provider=persistence)
    # create
    c = await engine.create("article", {"title": "A"}, context=CRUDContext())
    assert c.success
    eid = c.data["id"]
    # get
    g = await engine.get("article", eid)
    assert g.success
    assert g.data["id"] == eid
    # list
    l = await engine.list("article")
    assert l.success
    assert len(l.data) == 1
    # update
    u = await engine.update("article", eid, {"title": "B"})
    assert u.success
    assert u.data["title"] == "B"
    # delete
    d = await engine.delete("article", eid)
    assert d.success
    g2 = await engine.get("article", eid)
    assert g2.success is False


@pytest.mark.asyncio
async def test_universal_engine_list_with_filters():
    persistence = FakePersistence()
    engine = UniversalCRUDEngine(persistence_provider=persistence)
    await engine.create("article", {"title": "A", "status": "DRAFT"})
    await engine.create("article", {"title": "B", "status": "PUBLISHED"})
    res = await engine.list("article", filters={"status": "PUBLISHED"})
    assert res.success
    assert len(res.data) == 1
    assert res.data[0]["status"] == "PUBLISHED"


def test_product_info_is_metadata_only_not_execution():
    """
    Document Path B boundary: ProductInfo is metadata-only, not execution registry.
    C5 ProductRegistry list_products/get_product does not execute CRUD.
    """
    try:
        from ai_framework.product_registry import list_products, get_product

        products = list_products()
    except ImportError:
        # C5 registry API may expose different names — fallback to showcase_manifest or product module
        try:
            from ai_framework.product import list_products as lp, get_product as gp

            products = lp()
            get_product = gp
        except ImportError:
            # last fallback: just verify ProductInfo dataclass has no execution
            from ai_framework.product_registry import ProductInfo

            info = ProductInfo
            assert not hasattr(info, "execute")
            assert not hasattr(info, "create")
            return

    assert isinstance(products, list)
    if products:
        first = products[0]
        name = getattr(first, "name", first) if not isinstance(first, str) else first
        try:
            info = get_product(name)
        except Exception:
            info = first
        # ProductInfo must not have engine / execute attributes
        assert not hasattr(info, "execute")
        assert not hasattr(info, "create")
        assert not hasattr(info, "engine")
