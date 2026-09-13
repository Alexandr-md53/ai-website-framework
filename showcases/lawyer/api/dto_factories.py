# coding: utf-8, ASCII only
from typing import Dict, Any
import uuid
from showcases.lawyer.application.submit_request_use_case import (
    SubmitConsultationRequestDTO,
)
from showcases.lawyer.application.list_requests_use_case import (
    ListConsultationRequestsDTO,
)


def _get_body(data: Dict[str, Any]) -> Dict[str, Any]:
    if "body" in data and isinstance(data["body"], dict):
        return data["body"]
    return data


def _get_headers(data: Dict[str, Any]) -> Dict[str, str]:
    h = data.get("headers") or {}
    # normalize to lower for case-insensitive
    return {str(k).lower(): str(v) for k, v in h.items()}


def submit_request_dto_factory(data: Dict[str, Any]) -> SubmitConsultationRequestDTO:
    body = _get_body(data)
    return SubmitConsultationRequestDTO(
        client_name=body["client_name"],
        client_email=body["client_email"],
        attorney_id=str(body["attorney_id"]),
        service_id=str(body["service_id"]),
    )


def list_requests_dto_factory(data: Dict[str, Any]) -> ListConsultationRequestsDTO:
    headers = _get_headers(data)
    # Support both X-User-Role and direct role, plus query fallback
    role = (
        headers.get("x-user-role")
        or data.get("role")
        or _get_body(data).get("role")
        or ""
    )
    user_id = (
        headers.get("x-user-id")
        or headers.get("x-user_id")
        or data.get("user_id")
        or "anonymous"
    )
    attorney_id_raw = (
        headers.get("x-attorney-id")
        or headers.get("x-attorney_id")
        or data.get("attorney_id")
    )
    # also support query params if framework passes them
    query = data.get("query") or {}
    if not attorney_id_raw:
        attorney_id_raw = query.get("attorney_id") or query.get("attorneyId")

    attorney_id = None
    if attorney_id_raw:
        try:
            attorney_id = uuid.UUID(str(attorney_id_raw))
        except Exception:
            attorney_id = None

    return ListConsultationRequestsDTO(
        user_id=str(user_id),
        role=str(role),
        attorney_id=attorney_id,
    )
