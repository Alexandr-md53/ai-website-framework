# coding: utf-8, ASCII only
from typing import Dict, Tuple, Callable, Any, Optional
from ai_framework.product_registry import ProductInfo
from ai_framework.product.factory import build_app_from_product_info
from showcases.lawyer.services.lawyer_service import LawyerService
from showcases.lawyer.application.submit_request_use_case import (
    SubmitConsultationRequestUseCase,
)
from showcases.lawyer.application.list_requests_use_case import (
    ListConsultationRequestsUseCase,
)
from showcases.lawyer.api.dto_factories import (
    submit_request_dto_factory,
    list_requests_dto_factory,
)

_default_service: Optional[LawyerService] = None


def _get_default_service() -> LawyerService:
    global _default_service
    if _default_service is None:
        _default_service = LawyerService()
    return _default_service


def _make_use_case_map(
    service: LawyerService,
) -> Dict[Tuple[str, str], Tuple[Any, Callable[[Dict[str, Any]], Any]]]:
    submit_uc = SubmitConsultationRequestUseCase(service=service)
    list_uc = ListConsultationRequestsUseCase(service=service)
    return {
        ("POST", "/consultation-requests"): (submit_uc, submit_request_dto_factory),
        ("GET", "/consultation-requests"): (list_uc, list_requests_dto_factory),
    }


def build_lawyer_app(service_override: Optional[LawyerService] = None):
    service = service_override or _get_default_service()
    info = ProductInfo(
        name="lawyer",
        path="showcases/lawyer",
        manifest={
            "name": "lawyer",
            "product": "crud",
            "version": "10.2.0-c1",
            "package": "showcases.lawyer",
        },
    )
    use_case_map = _make_use_case_map(service)
    app = build_app_from_product_info(info, use_case_map)
    return app
