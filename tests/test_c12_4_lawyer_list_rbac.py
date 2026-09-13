import uuid
from decimal import Decimal


def _build_seeded_service_with_requests():
    from showcases.lawyer.domain.models import Attorney, PracticeArea, Service
    from showcases.lawyer.services.lawyer_service import LawyerService

    svc1 = Service(id=uuid.uuid4(), title="Corporate", base_fee=Decimal("100"))
    svc2 = Service(id=uuid.uuid4(), title="Family", base_fee=Decimal("200"))
    pa1 = PracticeArea(id=uuid.uuid4(), title="Corp Law", services=[svc1])
    pa2 = PracticeArea(id=uuid.uuid4(), title="Family Law", services=[svc2])
    att1 = Attorney(id=uuid.uuid4(), name="Alice", practice_areas=[pa1])
    att2 = Attorney(id=uuid.uuid4(), name="Bob", practice_areas=[pa2])
    service = LawyerService()
    service.register_attorney(att1)
    service.register_attorney(att2)
    service.submit_consultation_request("Client1", "c1@example.com", att1.id, svc1.id)
    service.submit_consultation_request("Client2", "c2@example.com", att1.id, svc1.id)
    service.submit_consultation_request("Client3", "c3@example.com", att2.id, svc2.id)
    return service, att1, att2


def _build_app(service):
    from showcases.lawyer.api.app_factory import build_lawyer_app

    return build_lawyer_app(service_override=service)


def test_c12_4_01_managing_partner_sees_all():
    from fastapi.testclient import TestClient

    service, att1, att2 = _build_seeded_service_with_requests()
    app = _build_app(service)
    client = TestClient(app)
    resp = client.get(
        "/consultation-requests", headers={"X-User-Role": "MANAGING_PARTNER"}
    )
    assert resp.status_code == 200
    data = resp.json()
    items = (
        data if isinstance(data, list) else data.get("items") or data.get("data") or []
    )
    assert len(items) == 3


def test_c12_4_02_attorney_sees_only_own():
    from fastapi.testclient import TestClient

    service, att1, att2 = _build_seeded_service_with_requests()
    app = _build_app(service)
    client = TestClient(app)
    resp = client.get(
        "/consultation-requests",
        headers={"X-User-Role": "ATTORNEY", "X-Attorney-Id": str(att1.id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    items = (
        data if isinstance(data, list) else data.get("items") or data.get("data") or []
    )
    assert len(items) == 2
    for item in items:
        aid = item.get("attorney_id")
        assert str(aid) == str(att1.id)
