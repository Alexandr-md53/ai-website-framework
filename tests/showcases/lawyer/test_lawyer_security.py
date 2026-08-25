import uuid
import pytest

from showcases.lawyer.services.lawyer_service import (
    LawyerService,
    LawyerUserRole,
    LawyerUserContext,
)


class TestLawyerSecurityDataIsolation:
    def test_attorney_can_only_see_own_assigned_requests(self):
        """Адвокат видит только те заявки, которые назначены лично ему."""
        attorney_1_id = uuid.uuid4()
        attorney_2_id = uuid.uuid4()

        service = LawyerService()

        req1 = service.create_request(
            client_name="Client A",
            client_email="a@example.com",
            attorney_id=attorney_1_id,
            service_id=uuid.uuid4(),
        )
        req2 = service.create_request(
            client_name="Client B",
            client_email="b@example.com",
            attorney_id=attorney_2_id,
            service_id=uuid.uuid4(),
        )

        attorney_1_context = LawyerUserContext(
            user_id="user-attorney-1",
            role=LawyerUserRole.ATTORNEY,
            attorney_id=attorney_1_id,
        )

        visible_requests = service.get_consultation_requests(user=attorney_1_context)

        assert len(visible_requests) == 1
        assert visible_requests[0].id == req1.id

    def test_managing_partner_can_see_all_requests(self):
        """Управляющий партнер имеет полный обзор всех заявок компании."""
        attorney_1_id = uuid.uuid4()
        attorney_2_id = uuid.uuid4()

        service = LawyerService()

        service.create_request(
            client_name="Client A",
            client_email="a@example.com",
            attorney_id=attorney_1_id,
            service_id=uuid.uuid4(),
        )
        service.create_request(
            client_name="Client B",
            client_email="b@example.com",
            attorney_id=attorney_2_id,
            service_id=uuid.uuid4(),
        )

        partner_context = LawyerUserContext(
            user_id="user-partner-1",
            role=LawyerUserRole.MANAGING_PARTNER,
        )

        visible_requests = service.get_consultation_requests(user=partner_context)

        assert len(visible_requests) == 2

