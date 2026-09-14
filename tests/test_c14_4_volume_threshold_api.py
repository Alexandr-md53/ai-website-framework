# coding: utf-8, ASCII only
from decimal import Decimal
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


def test_c14_4_01_volume_qty_5_no_discount(client):
    """C14.4.01 VOLUME qty=5 -> no discount (threshold >=10)"""
    resp = client.post(
        "/quotes",
        json={"unit_price": "1000.00", "quantity": 5, "discount_policy": "VOLUME"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # 5 * 1000 = 5000.00 without discount
    total = Decimal(str(data.get("total")))
    assert total == Decimal("5000.00"), f"expected 5000.00 no discount, got {data}"


def test_c14_4_02_volume_qty_10_discount(client):
    """C14.4.02 VOLUME qty=10 -> 10% discount"""
    resp = client.post(
        "/quotes",
        json={"unit_price": "1000.00", "quantity": 10, "discount_policy": "VOLUME"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # 10 * 1000 * 0.90 = 9000.00
    total = Decimal(str(data.get("total")))
    assert total == Decimal("9000.00"), f"expected 9000.00, got {data}"


def test_c14_4_03_volume_qty_15_discount(client):
    """C14.4.03 VOLUME qty=15 -> 10% discount"""
    resp = client.post(
        "/quotes",
        json={"unit_price": "1000.00", "quantity": 15, "discount_policy": "VOLUME"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # 15 * 1000 * 0.90 = 13500.00
    total = Decimal(str(data.get("total")))
    assert total == Decimal("13500.00"), f"expected 13500.00, got {data}"


def test_c14_4_04_none_seasonal_smoke(client):
    """C14.4.04 NONE/SEASONAL unchanged"""
    # NONE
    resp = client.post(
        "/quotes",
        json={"unit_price": "2000.00", "quantity": 2, "discount_policy": "NONE"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert Decimal(str(data.get("total"))) == Decimal("4000.00")

    # SEASONAL 15%
    resp2 = client.post(
        "/quotes",
        json={"unit_price": "2000.00", "quantity": 2, "discount_policy": "SEASONAL"},
    )
    assert resp2.status_code == 200, resp2.text
    data2 = resp2.json()
    assert Decimal(str(data2.get("total"))) == Decimal("3400.00"), (
        f"expected 3400.00 seasonal, got {data2}"
    )
