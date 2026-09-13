# coding: utf-8, ASCII only
from dataclasses import dataclass
import uuid
from showcases.lawyer.services.lawyer_service import LawyerService

@dataclass
class SubmitConsultationRequestDTO:
    client_name: str
    client_email: str
    attorney_id: str
    service_id: str

@dataclass
class ConsultationRequestResponse:
    id: str
    client_name: str
    client_email: str
    attorney_id: str
    service_id: str

class SubmitConsultationRequestUseCase:
    def __init__(self, service: LawyerService):
        self._service = service

    def execute(self, dto: SubmitConsultationRequestDTO):
        try:
            req = self._service.submit_consultation_request(
                client_name=dto.client_name,
                client_email=dto.client_email,
                attorney_id=uuid.UUID(dto.attorney_id),
                service_id=uuid.UUID(dto.service_id),
            )
            return ConsultationRequestResponse(
                id=str(req.id),
                client_name=req.client_name,
                client_email=req.client_email,
                attorney_id=str(req.attorney_id),
                service_id=str(req.service_id),
            )
        except ValueError as e:
            return {"status": 400, "json": {"success": False, "error": str(e), "code": "VALIDATION_ERROR", "errors": [{"code": "VALIDATION_ERROR", "message": str(e)}]}, "success": False}
