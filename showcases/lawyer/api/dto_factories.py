# coding: utf-8, ASCII only
from typing import Dict, Any
import uuid
from showcases.lawyer.application.submit_request_use_case import SubmitConsultationRequestDTO
from showcases.lawyer.application.list_requests_use_case import ListConsultationRequestsDTO
from showcases.lawyer.application.update_request_status_use_case import UpdateConsultationStatusDTO

def _get_body(data: Dict[str, Any]) -> Dict[str, Any]:
    if "body" in data and isinstance(data["body"], dict):
        return data["body"]
    return data

def _get_headers(data: Dict[str, Any]) -> Dict[str, str]:
    h = data.get("headers") or {}
    return {str(k).lower(): str(v) for k, v in h.items()}

def submit_request_dto_factory(data: Dict[str, Any]) -> SubmitConsultationRequestDTO:
    body = _get_body(data)
    return SubmitConsultationRequestDTO(client_name=body["client_name"], client_email=body["client_email"], attorney_id=str(body["attorney_id"]), service_id=str(body["service_id"]))

def list_requests_dto_factory(data: Dict[str, Any]) -> ListConsultationRequestsDTO:
    headers = _get_headers(data)
    role = headers.get("x-user-role") or data.get("role") or _get_body(data).get("role") or ""
    user_id = headers.get("x-user-id") or data.get("user_id") or "anonymous"
    attorney_id_raw = headers.get("x-attorney-id") or data.get("attorney_id")
    attorney_id = None
    if attorney_id_raw:
        try:
            attorney_id = uuid.UUID(str(attorney_id_raw))
        except Exception:
            attorney_id = None
    return ListConsultationRequestsDTO(user_id=str(user_id), role=str(role), attorney_id=attorney_id)

def update_status_dto_factory(data: Dict[str, Any]) -> UpdateConsultationStatusDTO:
    headers = _get_headers(data)
    body = _get_body(data)
    path_params = data.get("path_params") or {}
    request_id = path_params.get("id") or data.get("id") or body.get("id") or ""
    status_val = body.get("status") or data.get("status") or ""
    role = headers.get("x-user-role") or data.get("role") or body.get("role") or ""
    user_id = headers.get("x-user-id") or data.get("user_id") or "anonymous"
    attorney_id_raw = headers.get("x-attorney-id") or data.get("attorney_id")
    attorney_id = None
    if attorney_id_raw:
        try:
            attorney_id = uuid.UUID(str(attorney_id_raw))
        except Exception:
            attorney_id = None
    return UpdateConsultationStatusDTO(request_id=str(request_id), status=str(status_val), user_id=str(user_id), role=str(role), attorney_id=attorney_id)
