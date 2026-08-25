from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
import uuid

from showcases.lawyer.domain.models import Attorney, Service, ConsultationRequest
from showcases.lawyer.domain.validators import ConsultationRequestValidator


class LawyerUserRole(str, Enum):
    ATTORNEY = "ATTORNEY"
    MANAGING_PARTNER = "MANAGING_PARTNER"


@dataclass
class LawyerUserContext:
    user_id: str
    role: LawyerUserRole
    attorney_id: Optional[uuid.UUID] = None


class LawyerService:
    def __init__(self) -> None:
        self._attorneys: Dict[uuid.UUID, Attorney] = {}
        self._requests: List[ConsultationRequest] = []
        self._validator = ConsultationRequestValidator()

    def register_attorney(self, attorney: Attorney) -> None:
        """Регистрация адвоката в реестре фирмы."""
        self._attorneys[attorney.id] = attorney

    def _find_service_by_id(self, service_id: uuid.UUID) -> Service:
        """Поиск услуги в реестре зарегистрированных адвокатов."""
        for att in self._attorneys.values():
            for pa in att.practice_areas:
                for s in pa.services:
                    if s.id == service_id:
                        return s
        return Service(id=service_id, title="Unknown Service")

    def submit_consultation_request(
        self,
        client_name: str,
        client_email: str,
        attorney_id: uuid.UUID,
        service_id: uuid.UUID,
    ) -> ConsultationRequest:
        """Валидированная подача заявки на первичную консультацию."""
        attorney = self._attorneys.get(attorney_id)
        service = self._find_service_by_id(service_id)

        request = ConsultationRequest(
            id=uuid.uuid4(),
            client_name=client_name,
            client_email=client_email,
            attorney_id=attorney_id,
            service_id=service_id,
        )

        errors = self._validator.validate(request, attorney=attorney, service=service)
        if errors:
            raise ValueError("; ".join(errors))

        self._requests.append(request)
        return request

    def create_request(
        self,
        client_name: str,
        client_email: str,
        attorney_id: uuid.UUID,
        service_id: uuid.UUID,
    ) -> ConsultationRequest:
        """Создание базовой заявки без обязательной проверки реестра (для юнит-тестов безопасности)."""
        req = ConsultationRequest(
            id=uuid.uuid4(),
            client_name=client_name,
            client_email=client_email,
            attorney_id=attorney_id,
            service_id=service_id,
        )
        self._requests.append(req)
        return req

    def get_consultation_requests(
        self,
        user: LawyerUserContext,
    ) -> List[ConsultationRequest]:
        if user.role == LawyerUserRole.MANAGING_PARTNER:
            return list(self._requests)

        if user.role == LawyerUserRole.ATTORNEY:
            return [
                req for req in self._requests if req.attorney_id == user.attorney_id
            ]

        return []
