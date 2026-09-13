# coding: utf-8, ASCII only
import uuid
from fastapi.testclient import TestClient
import pytest

from showcases.plant_nursery.domain.category import Category
from tests.showcases.plant_nursery.conftest import InMemoryCategoryRepository


def _build_app_with_repo(repo):
    from showcases.plant_nursery.api.app_factory import build_plant_nursery_app
    from showcases.plant_nursery.services.catalog_service import (
        PlantNurseryCatalogService,
    )

    service = PlantNurseryCatalogService(category_repo=repo)
    app = build_plant_nursery_app(service_override=service)
    return app, service


def test_c13_2_01_valid_hierarchy():
    """C13.2.01 valid category hierarchy -> success"""
    repo = InMemoryCategoryRepository()
    parent = Category(
        id=uuid.uuid4(), name="Outdoor Plants", slug="outdoor-plants", parent_id=None
    )
    repo.add(parent)

    app, _ = _build_app_with_repo(repo)
    client = TestClient(app)

    payload = {
        "name": "Shrubs",
        "slug": "shrubs",
        "parent_id": str(parent.id),
    }

    resp = client.post("/categories", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    # expect created category returned
    assert data.get("name") == "Shrubs" or data.get("slug") == "shrubs"
    assert data.get("parent_id") == str(parent.id)


def test_c13_2_02_self_reference():
    """C13.2.02 self-reference -> 400 validation.self_reference"""
    repo = InMemoryCategoryRepository()
    app, _ = _build_app_with_repo(repo)
    client = TestClient(app)

    cat_id = uuid.uuid4()
    payload = {
        "id": str(cat_id),
        "name": "Self Ref",
        "slug": "self-ref",
        "parent_id": str(cat_id),
    }

    resp = client.post("/categories", json=payload)
    assert resp.status_code == 400, resp.text
    text = resp.text.lower()
    assert "self_reference" in text


def test_c13_2_03_not_found():
    """C13.2.03 missing parent -> 400 validation.not_found"""
    repo = InMemoryCategoryRepository()
    app, _ = _build_app_with_repo(repo)
    client = TestClient(app)

    missing = uuid.uuid4()
    payload = {
        "name": "Orphan",
        "slug": "orphan",
        "parent_id": str(missing),
    }

    resp = client.post("/categories", json=payload)
    assert resp.status_code == 400, resp.text
    assert "not_found" in resp.text.lower()


def test_c13_2_04_cyclic_dependency():
    """C13.2.04 cyclic A->B->A -> 400 validation.cyclic_dependency"""
    repo = InMemoryCategoryRepository()
    cat_a = Category(id=uuid.uuid4(), name="A", slug="a", parent_id=None)
    cat_b = Category(id=uuid.uuid4(), name="B", slug="b", parent_id=cat_a.id)
    repo.add(cat_a)
    repo.add(cat_b)

    app, _ = _build_app_with_repo(repo)
    client = TestClient(app)

    # try to set A's parent to B => cycle A->B->A
    payload = {
        "id": str(cat_a.id),
        "name": cat_a.name,
        "slug": cat_a.slug,
        "parent_id": str(cat_b.id),
    }

    resp = client.post("/categories", json=payload)
    # could be POST /categories/{id} or POST /categories with id - we accept either 400
    assert resp.status_code == 400, resp.text
    assert "cyclic_dependency" in resp.text.lower()
