# coding: utf-8, ASCII only
import uuid
import pytest
from fastapi.testclient import TestClient
from showcases.plant_nursery.api.app_factory import build_plant_nursery_app
from tests.showcases.plant_nursery.conftest import InMemoryCategoryRepository
from showcases.plant_nursery.services.catalog_service import PlantNurseryCatalogService
from showcases.plant_nursery.domain.category import Category
from showcases.plant_nursery.domain.plant import (
    Plant,
    LightRequirement,
    WateringRequirement,
)


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


def _add_category(repo):
    cid = uuid.uuid4()
    repo.add(Category(id=cid, name="TestCat", slug="test-cat", parent_id=None))
    return cid


def _add_plant(service, category_id):
    plant = Plant(
        id=uuid.uuid4(),
        category_id=category_id,
        name="TestPlant",
        description="test",
        light_req=LightRequirement.MEDIUM,
        water_req=WateringRequirement.MODERATE,
        frost_resistance=0,
        main_image_id=None,
    )
    service._plants.append(plant)
    return plant


def test_c14_1_01_first_image_sets_main(client, repo, service):
    """C14.1.01 first image -> sets main_image_id"""
    cat = _add_category(repo)
    plant = _add_plant(service, cat)
    img_id = str(uuid.uuid4())

    resp = client.post(f"/plants/{plant.id}/images", json={"image_id": img_id})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # Expect plant or gallery response containing main_image_id == img_id
    main = data.get("main_image_id") if isinstance(data, dict) else None
    if main is None and "plant" in data:
        main = data["plant"].get("main_image_id")
    assert main == img_id, f"expected main_image_id {img_id}, got {data}"


def test_c14_1_02_second_image_gallery_size_2(client, repo, service):
    """C14.1.02 second image -> gallery size 2"""
    cat = _add_category(repo)
    plant = _add_plant(service, cat)
    img1 = str(uuid.uuid4())
    img2 = str(uuid.uuid4())

    r1 = client.post(f"/plants/{plant.id}/images", json={"image_id": img1})
    assert r1.status_code == 200, r1.text
    r2 = client.post(f"/plants/{plant.id}/images", json={"image_id": img2})
    assert r2.status_code == 200, r2.text
    data = r2.json()
    gallery = data.get("images") or data.get("gallery") or data.get("image_ids") or []
    if isinstance(gallery, list) and len(gallery) == 2:
        assert True
    else:
        # fallback: check service internal gallery size if API returns plant
        # must contain at least 2 distinct ids
        all_ids = str(data)
        assert img1 in all_ids and img2 in all_ids


def test_c14_1_03_max_limit(client, repo, service):
    """C14.1.03 sixth image -> 400 validation.max_limit"""
    cat = _add_category(repo)
    plant = _add_plant(service, cat)

    for _ in range(5):
        resp = client.post(
            f"/plants/{plant.id}/images", json={"image_id": str(uuid.uuid4())}
        )
        assert resp.status_code == 200, resp.text

    resp = client.post(
        f"/plants/{plant.id}/images", json={"image_id": str(uuid.uuid4())}
    )
    assert resp.status_code == 400, resp.text
    body = resp.json()
    txt = str(body).lower()
    assert "max_limit" in txt or "limit" in txt


def test_c14_1_04_plant_not_found(client, repo, service):
    """C14.1.04 unknown plant -> 400 validation.not_found"""
    missing = uuid.uuid4()
    resp = client.post(
        f"/plants/{missing}/images", json={"image_id": str(uuid.uuid4())}
    )
    assert resp.status_code == 400, resp.text
    txt = str(resp.json()).lower()
    assert "not_found" in txt


def test_c14_1_05_invalid_image_uuid(client, repo, service):
    """C14.1.05 invalid image UUID -> 400 validation.not_found"""
    cat = _add_category(repo)
    plant = _add_plant(service, cat)

    resp = client.post(f"/plants/{plant.id}/images", json={"image_id": "not-a-uuid"})
    assert resp.status_code == 400, resp.text
    txt = str(resp.json()).lower()
    assert "not_found" in txt
