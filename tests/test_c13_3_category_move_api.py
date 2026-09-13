# coding: utf-8, ASCII only
import uuid
import pytest
from fastapi.testclient import TestClient
from showcases.plant_nursery.api.app_factory import build_plant_nursery_app
from tests.showcases.plant_nursery.conftest import InMemoryCategoryRepository
from showcases.plant_nursery.services.catalog_service import PlantNurseryCatalogService


@pytest.fixture
def repo():
    return InMemoryCategoryRepository()


@pytest.fixture
def service(repo):
    return PlantNurseryCatalogService(category_repo=repo)


@pytest.fixture
def client(service):
    app = build_plant_nursery_app(service_override=service)
    return TestClient(app)


def _create_category(client, name, slug, parent_id=None):
    payload = {"name": name, "slug": slug}
    if parent_id is not None:
        payload["parent_id"] = str(parent_id)
    else:
        payload["parent_id"] = None
    # Use C13.2 endpoint to create
    resp = client.post("/categories", json=payload)
    # For RED phase, this may already work (C13.2 GREEN)
    return resp


def test_c13_3_01_valid_move(client, repo):
    """C13.3.01 valid move - move child to another parent"""
    root = uuid.uuid4()
    parent_a = uuid.uuid4()
    parent_b = uuid.uuid4()
    child = uuid.uuid4()

    from showcases.plant_nursery.domain.category import Category

    repo.add(Category(id=root, name="Root", slug="root", parent_id=None))
    repo.add(Category(id=parent_a, name="A", slug="a", parent_id=root))
    repo.add(Category(id=parent_b, name="B", slug="b", parent_id=root))
    repo.add(Category(id=child, name="Child", slug="child", parent_id=parent_a))

    resp = client.put(f"/categories/{child}/parent", json={"parent_id": str(parent_b)})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == str(child)
    assert data["parent_id"] == str(parent_b)


def test_c13_3_02_self_reference(client, repo):
    """C13.3.02 self-reference - parent_id == id"""
    cat_id = uuid.uuid4()
    from showcases.plant_nursery.domain.category import Category

    repo.add(Category(id=cat_id, name="Self", slug="self", parent_id=None))

    resp = client.put(f"/categories/{cat_id}/parent", json={"parent_id": str(cat_id)})
    assert resp.status_code == 400, resp.text
    data = resp.json()
    assert data["success"] is False
    # expect self_reference key
    errors = data.get("errors", [])
    assert any(
        "self_reference" in (e.get("message") or e.get("message_key") or "")
        for e in errors
    ) or "self_reference" in data.get("error", "")


def test_c13_3_03_not_found(client, repo):
    """C13.3.03 not_found - category or parent not found"""
    existing = uuid.uuid4()
    missing = uuid.uuid4()
    from showcases.plant_nursery.domain.category import Category

    repo.add(Category(id=existing, name="Exist", slug="exist", parent_id=None))

    # case 1: category id not found
    resp1 = client.put(
        f"/categories/{missing}/parent", json={"parent_id": str(existing)}
    )
    assert resp1.status_code == 400, resp1.text

    # case 2: parent not found
    resp2 = client.put(
        f"/categories/{existing}/parent", json={"parent_id": str(missing)}
    )
    assert resp2.status_code == 400, resp2.text
    data = resp2.json()
    assert data["success"] is False


def test_c13_3_04_cyclic_dependency(client, repo):
    """C13.3.04 cyclic dependency - A->B->C, move A under C"""
    a = uuid.uuid4()
    b = uuid.uuid4()
    c = uuid.uuid4()
    from showcases.plant_nursery.domain.category import Category

    repo.add(Category(id=a, name="A", slug="a", parent_id=None))
    repo.add(Category(id=b, name="B", slug="b", parent_id=a))
    repo.add(Category(id=c, name="C", slug="c", parent_id=b))

    resp = client.put(f"/categories/{a}/parent", json={"parent_id": str(c)})
    assert resp.status_code == 400, resp.text
    data = resp.json()
    assert data["success"] is False
    errors = data.get("errors", [])
    assert any(
        "cyclic_dependency" in (e.get("message") or e.get("message_key") or "")
        for e in errors
    ) or "cyclic_dependency" in data.get("error", "")


def test_c13_3_05_move_to_root(client, repo):
    """C13.3.05 move to root - parent_id null"""
    parent = uuid.uuid4()
    child = uuid.uuid4()
    from showcases.plant_nursery.domain.category import Category

    repo.add(Category(id=parent, name="Parent", slug="parent", parent_id=None))
    repo.add(Category(id=child, name="Child", slug="child", parent_id=parent))

    resp = client.put(f"/categories/{child}/parent", json={"parent_id": None})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == str(child)
    assert data["parent_id"] is None
