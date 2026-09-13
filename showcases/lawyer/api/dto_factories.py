# coding: utf-8, ASCII only
from typing import Dict, Any
from showcases.lawyer.application.submit_request_use_case import SubmitConsultationRequestDTO

def _get_body(data: Dict[str, Any]) -> Dict[str, Any]:
    if "body" in data and isinstance(data["body"], dict):
        return data["body"]
    return data

def submit_request_dto_factory(data: Dict[str, Any]) -> SubmitConsultationRequestDTO:
    body = _get_body(data)
    return SubmitConsultationRequestDTO(
        client_name=body["client_name"],
        client_email=body["client_email"],
        attorney_id=str(body["attorney_id"]),
        service_id=str(body["service_id"]),
    )
