# coding: utf-8, ASCII only
"""
C15.1 RED-only: Lawyer Consultation Status Lifecycle
PUT /consultation-requests/{id}/status

Expected contract (to be implemented):
- Models add ConsultationStatus enum + status=PENDING default
- LawyerService.update_request_status(id, new_status, user)
- UseCase UpdateConsultationStatusUseCase
- API: PUT /consultation-requests/{id}/status {status}
- RBAC: MANAGING_PARTNER any, ATTORNEY only own
- Transitions: PENDING->APPROVED|REJECTED, APPROVED->COMPLETED, REJECTED/COMPLETED terminal
- Errors: 404 validation.not_found id, 403 forbidden role, 400 invalid_transition status
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from showcases.lawyer.domain.models import Service, PracticeArea, Attorney
from showcases.lawyer.services.lawyer_service import LawyerService
from showcases.lawyer.api.app_factory import build_lawyer_app


def _setup_service_with_attorneys():
    service = LawyerService()
    svc = Service(id=uuid.uuid4(), title="Consultation")
    pa = PracticeArea(id=uuid.uuid4(), title="General", services=[svc])
    att1 = Attorney(id=uuid.uuid4(), name="Attorney One", practice_areas=[pa])
    att2 = Attorney(id=uuid.uuid4(), name="Attorney Two", practice_areas=[pa])
    service.register_attorney(att1)
    service.register_attorney(att2)
    # create request for att1 via create_request to bypass validation
    req = service.create_request(
        client_name="John Doe",
        client_email="john@example.com",
        attorney_id=att1.id,
        service_id=svc.id,
    )
    return service, att1, att2, req, svc


@pytest.fixture
def setup():
    return _setup_service_with_attorneys()


@pytest.fixture
def client(setup):
    service, _, _, _, _ = setup
    app = build_lawyer_app(service_override=service)
    return TestClient(app)


def test_c15_1_01_update_status_approved_by_manager(setup, client):
    """C15.1.01 MANAGING_PARTNER can approve PENDING -> APPROVED"""
    service, att1, att2, req, _ = setup
    resp = client.put(
        f"/consultation-requests/{req.id}/status",
        json={"status": "APPROVED"},
        headers={"X-User-Id": "manager-1", "X-User-Role": "MANAGING_PARTNER"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == str(req.id)
    assert data["status"] == "APPROVED"


def test_c15_1_02_update_status_by_own_attorney(setup, client):
    """C15.1.02 ATTORNEY can update own request"""
    service, att1, att2, req, _ = setup
    resp = client.put(
        f"/consultation-requests/{req.id}/status",
        json={"status": "REJECTED"},
        headers={
            "X-User-Id": "att-1",
            "X-User-Role": "ATTORNEY",
            "X-Attorney-Id": str(att1.id),
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "REJECTED"


def test_c15_1_03_forbidden_other_attorney(setup, client):
    """C15.1.03 ATTORNEY cannot update other attorney's request -> 403/400 validation"""
    service, att1, att2, req, _ = setup
    resp = client.put(
        f"/consultation-requests/{req.id}/status",
        json={"status": "APPROVED"},
        headers={
            "X-User-Id": "att-2",
            "X-User-Role": "ATTORNEY",
            "X-Attorney-Id": str(att2.id),
        },
    )
    # Expect forbidden
    assert resp.status_code in (403, 400), resp.text
    # if framework returns validation structure
    if resp.status_code == 400:
        assert (
            "forbidden" in resp.text.lower()
            or "role" in resp.text.lower()
            or "not" in resp.text.lower()
        )


def test_c15_1_04_not_found(setup, client):
    """C15.1.04 unknown id -> 404 / validation.not_found"""
    _, _, _, _, _ = setup
    fake_id = uuid.uuid4()
    resp = client.put(
        f"/consultation-requests/{fake_id}/status",
        json={"status": "APPROVED"},
        headers={"X-User-Id": "manager-1", "X-User-Role": "MANAGING_PARTNER"},
    )
    assert resp.status_code in (404, 400), resp.text


def test_c15_1_05_invalid_transition(setup, client):
    """C15.1.05 APPROVED -> REJECTED should be invalid (only COMPLETED allowed after APPROVED)"""
    service, att1, att2, req, _ = setup
    # First approve
    resp1 = client.put(
        f"/consultation-requests/{req.id}/status",
        json={"status": "APPROVED"},
        headers={"X-User-Id": "manager-1", "X-User-Role": "MANAGING_PARTNER"},
    )
    assert resp1.status_code == 200, resp1.text
    # Then try invalid REJECTED
    resp2 = client.put(
        f"/consultation-requests/{req.id}/status",
        json={"status": "REJECTED"},
        headers={"X-User-Id": "manager-1", "X-User-Role": "MANAGING_PARTNER"},
    )
    assert resp2.status_code == 400, resp2.text
    assert "transition" in resp2.text.lower() or "invalid" in resp2.text.lower()
