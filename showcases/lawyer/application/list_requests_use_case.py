# coding: utf-8, ASCII only
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import uuid
from showcases.lawyer.services.lawyer_service import (
    LawyerService,
    LawyerUserContext,
    LawyerUserRole,
)


@dataclass
class ListConsultationRequestsDTO:
    user_id: str
    role: str
    attorney_id: Optional[uuid.UUID] = None


class ListConsultationRequestsUseCase:
    def __init__(self, service: LawyerService):
        self._service = service

    def execute(self, dto: ListConsultationRequestsDTO) -> List[Dict[str, Any]]:
        try:
            role = LawyerUserRole(dto.role)
        except Exception:
            try:
                role = LawyerUserRole[dto.role.upper()]
            except Exception:
                return []

        user_ctx = LawyerUserContext(
            user_id=dto.user_id,
            role=role,
            attorney_id=dto.attorney_id,
        )

        requests = self._service.get_consultation_requests(user=user_ctx)
        result = []
        for r in requests:
            result.append(
                {
                    "id": str(r.id),
                    "client_name": r.client_name,
                    "client_email": r.client_email,
                    "attorney_id": str(r.attorney_id),
                    "service_id": str(r.service_id),
                }
            )
        return result
