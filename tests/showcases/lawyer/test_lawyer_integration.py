from decimal import Decimal
import uuid
import pytest

from showcases.lawyer.domain.models import Attorney, PracticeArea, Service
from showcases.lawyer.services.lawyer_service import (
    LawyerService,
    LawyerUserRole,
    LawyerUserContext,
)


class TestLawyerIntegrationScenario:
    def test_full_consultation_booking_and_isolation_workflow(self):
        """Сквозной сценарий: связь M2M, валидированная запись на услугу и ролевая изоляция."""
        service = LawyerService()

        # 1. Настройка структур практик и услуг
        ip_service = Service(
            id=uuid.uuid4(), title="IP Law", base_fee=Decimal("1500.00")
        )
        tax_service = Service(
            id=uuid.uuid4(), title="Tax Advice", base_fee=Decimal("1000.00")
        )

        ip_area = PracticeArea(
            id=uuid.uuid4(), title="Intellectual Property", services=[ip_service]
        )
        tax_area = PracticeArea(
            id=uuid.uuid4(), title="Taxation", services=[tax_service]
        )

        attorney_1 = Attorney(
            id=uuid.uuid4(), name="Harvey Specter", practice_areas=[ip_area]
        )
        attorney_2 = Attorney(
            id=uuid.uuid4(), name="Louis Litt", practice_areas=[tax_area]
        )

        service.register_attorney(attorney_1)
        service.register_attorney(attorney_2)

        # 2. Успешная подача заявки
        req1 = service.submit_consultation_request(
            client_name="John Doe",
            client_email="john@example.com",
            attorney_id=attorney_1.id,
            service_id=ip_service.id,
        )
        assert req1.id is not None

        # 3. Отклонение заявки (Харви не оказывает налоговых консультаций)
        with pytest.raises(
            ValueError, match="Attorney does not provide the requested service"
        ):
            service.submit_consultation_request(
                client_name="Jane Doe",
                client_email="jane@example.com",
                attorney_id=attorney_1.id,
                service_id=tax_service.id,
            )

        # 4. Проверка изоляции видимости заявок
        attorney_context = LawyerUserContext(
            user_id="u1",
            role=LawyerUserRole.ATTORNEY,
            attorney_id=attorney_1.id,
        )
        partner_context = LawyerUserContext(
            user_id="u2",
            role=LawyerUserRole.MANAGING_PARTNER,
        )

        assert len(service.get_consultation_requests(attorney_context)) == 1
        assert len(service.get_consultation_requests(partner_context)) == 1
