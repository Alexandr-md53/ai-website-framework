# coding: utf-8, ASCII only
"""
C12.3: Lawyer submit_consultation_request via C10.1 factory
M2M: Attorney -> PracticeArea -> Service
"""
import uuid
from decimal import Decimal
import pytest

def _build_seeded_app():
    # Import here to avoid collection-time side effects
    from showcases.lawyer.api.app_factory import build_lawyer_app
    from showcases.lawyer.domain.models import Attorney, PracticeArea, Service
    from showcases.lawyer.services.lawyer_service import LawyerService

    # Create known service + attorney graph
    svc = Service(id=uuid.uuid4(), title="Corporate Incorporation", base_fee=Decimal("500.00"))
    other_svc = Service(id=uuid.uuid4(), title="Trademark Filing", base_fee=Decimal("300.00"))
    pa = PracticeArea(id=uuid.uuid4(), title="Corporate Law", services=[svc])
    att = Attorney(id=uuid.uuid4(), name="Jane Doe", practice_areas=[pa])

    service = LawyerService()
    service.register_attorney(att)

    app = build_lawyer_app(service_override=service)
    return app, att, svc, other_svc

def test_c12_3_01_valid_submit_succeeds():
    from fastapi.testclient import TestClient
    app, attorney, service, _ = _build_seeded_app()
    client = TestClient(app)

    resp = client.post("/consultation-requests", json={
        "client_name": "John Client",
        "client_email": "john@example.com",
        "attorney_id": str(attorney.id),
        "service_id": str(service.id),
    })
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["client_email"] == "john@example.com"

def test_c12_3_02_invalid_email_validation_error():
    from fastapi.testclient import TestClient
    app, attorney, service, _ = _build_seeded_app()
    client = TestClient(app)

    resp = client.post("/consultation-requests", json={
        "client_name": "John Client",
        "client_email": "invalid-email",
        "attorney_id": str(attorney.id),
        "service_id": str(service.id),
    })
    assert resp.status_code in (400, 422)

def test_c12_3_03_attorney_does_not_provide_service():
    from fastapi.testclient import TestClient
    app, attorney, _, other_service = _build_seeded_app()
    client = TestClient(app)

    resp = client.post("/consultation-requests", json={
        "client_name": "John Client",
        "client_email": "john@example.com",
        "attorney_id": str(attorney.id),
        "service_id": str(other_service.id),
    })
    # Validator should reject: Attorney does not provide the requested service
    assert resp.status_code in (400, 422)
