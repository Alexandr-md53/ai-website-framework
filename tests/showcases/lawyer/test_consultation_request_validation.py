from decimal import Decimal
import uuid
import pytest

from showcases.lawyer.domain.models import (
    Attorney,
    PracticeArea,
    Service,
    ConsultationRequest,
)
from showcases.lawyer.domain.validators import ConsultationRequestValidator


class TestConsultationRequestValidation:
    def test_valid_consultation_request(self):
        """Успешная валидация корректной заявки на консультацию."""
        service = Service(
            id=uuid.uuid4(), title="IP Patent Filing", base_fee=Decimal("1500.00")
        )
        practice_area = PracticeArea(
            id=uuid.uuid4(), title="Intellectual Property", services=[service]
        )
        attorney = Attorney(
            id=uuid.uuid4(), name="Rachel Zane", practice_areas=[practice_area]
        )

        request = ConsultationRequest(
            id=uuid.uuid4(),
            client_name="Alex Smith",
            client_email="alex@example.com",
            attorney_id=attorney.id,
            service_id=service.id,
        )

        validator = ConsultationRequestValidator()
        errors = validator.validate(request, attorney=attorney, service=service)
        assert len(errors) == 0

    def test_reject_request_if_attorney_does_not_provide_service(self):
        """Отказ в валидации, если выбранный адвокат не оказывает запрошенную услугу."""
        service_ip = Service(
            id=uuid.uuid4(), title="IP Patent Filing", base_fee=Decimal("1500.00")
        )
        service_tax = Service(
            id=uuid.uuid4(), title="Tax Audit", base_fee=Decimal("2000.00")
        )

        practice_area = PracticeArea(
            id=uuid.uuid4(), title="Intellectual Property", services=[service_ip]
        )
        attorney = Attorney(
            id=uuid.uuid4(), name="Rachel Zane", practice_areas=[practice_area]
        )

        request = ConsultationRequest(
            id=uuid.uuid4(),
            client_name="Alex Smith",
            client_email="alex@example.com",
            attorney_id=attorney.id,
            service_id=service_tax.id,
        )

        validator = ConsultationRequestValidator()
        errors = validator.validate(request, attorney=attorney, service=service_tax)
        assert "Attorney does not provide the requested service" in errors

    def test_reject_request_with_invalid_email(self):
        """Отказ в валидации при некорректном формате e-mail клиента."""
        service = Service(
            id=uuid.uuid4(), title="IP Patent Filing", base_fee=Decimal("1500.00")
        )
        practice_area = PracticeArea(
            id=uuid.uuid4(), title="Intellectual Property", services=[service]
        )
        attorney = Attorney(
            id=uuid.uuid4(), name="Rachel Zane", practice_areas=[practice_area]
        )

        request = ConsultationRequest(
            id=uuid.uuid4(),
            client_name="Alex Smith",
            client_email="invalid-email-format",
            attorney_id=attorney.id,
            service_id=service.id,
        )

        validator = ConsultationRequestValidator()
        errors = validator.validate(request, attorney=attorney, service=service)
        assert "Invalid client email address" in errors
