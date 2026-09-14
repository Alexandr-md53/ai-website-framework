# coding: utf-8, ASCII only
from dataclasses import dataclass
from typing import Optional, Dict, Any
import uuid
from showcases.lawyer.services.lawyer_service import (
    LawyerService,
    LawyerUserContext,
    LawyerUserRole,
)
from showcases.lawyer.domain.models import ConsultationStatus


@dataclass
class UpdateConsultationStatusDTO:
    request_id: str
    status: str
    user_id: str
    role: str
    attorney_id: Optional[uuid.UUID] = None


@dataclass
class UpdateStatusResponse:
    id: str
    client_name: str
    client_email: str
    attorney_id: str
    service_id: str
    status: str


class UpdateConsultationStatusUseCase:
    def __init__(self, service: LawyerService):
        self._service = service

    def execute(self, dto: UpdateConsultationStatusDTO):
        # Parse request_id
        try:
            req_id = uuid.UUID(dto.request_id)
        except Exception:
            return {
                "status": 404,
                "json": {
                    "success": False,
                    "code": "VALIDATION_ERROR",
                    "errors": [{"field": "id", "code": "validation.not_found"}],
                },
                "success": False,
            }

        # Parse status
        try:
            new_status = ConsultationStatus(dto.status)
        except Exception:
            try:
                new_status = ConsultationStatus[dto.status.upper()]
            except Exception:
                return {
                    "status": 400,
                    "json": {
                        "success": False,
                        "code": "VALIDATION_ERROR",
                        "errors": [
                            {"field": "status", "code": "validation.invalid_status"}
                        ],
                    },
                    "success": False,
                }

        # Parse role
        try:
            role = LawyerUserRole(dto.role)
        except Exception:
            try:
                role = LawyerUserRole[dto.role.upper()]
            except Exception:
                return {
                    "status": 403,
                    "json": {
                        "success": False,
                        "code": "VALIDATION_ERROR",
                        "errors": [{"field": "role", "code": "validation.forbidden"}],
                    },
                    "success": False,
                }

        user_ctx = LawyerUserContext(
            user_id=dto.user_id,
            role=role,
            attorney_id=dto.attorney_id,
        )

        try:
            req = self._service.update_request_status(
                request_id=req_id, new_status=new_status, user=user_ctx
            )
            return UpdateStatusResponse(
                id=str(req.id),
                client_name=req.client_name,
                client_email=req.client_email,
                attorney_id=str(req.attorney_id),
                service_id=str(req.service_id),
                status=req.status.value,
            )
        except LookupError:
            return {
                "status": 404,
                "json": {
                    "success": False,
                    "code": "VALIDATION_ERROR",
                    "errors": [{"field": "id", "code": "validation.not_found"}],
                },
                "success": False,
            }
        except PermissionError:
            return {
                "status": 403,
                "json": {
                    "success": False,
                    "code": "VALIDATION_ERROR",
                    "errors": [{"field": "role", "code": "validation.forbidden"}],
                },
                "success": False,
            }
        except ValueError as e:
            msg = str(e)
            if "transition" in msg.lower():
                return {
                    "status": 400,
                    "json": {
                        "success": False,
                        "code": "VALIDATION_ERROR",
                        "errors": [
                            {
                                "field": "status",
                                "code": "validation.invalid_transition",
                                "message": msg,
                            }
                        ],
                    },
                    "success": False,
                }
            return {
                "status": 400,
                "json": {
                    "success": False,
                    "error": msg,
                    "code": "VALIDATION_ERROR",
                    "errors": [{"code": "VALIDATION_ERROR", "message": msg}],
                },
                "success": False,
            }
