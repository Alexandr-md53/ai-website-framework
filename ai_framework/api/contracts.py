from dataclasses import dataclass, field
from typing import Any, List, Optional

from ai_framework.crud.contracts import CRUDError, CRUDResult


@dataclass
class APIResponse:
    """Единый канонический формат HTTP-ответа (API Envelope)."""

    success: bool
    data: Optional[Any] = None
    errors: List[dict] = field(default_factory=list)
    operation: Optional[str] = None

    def to_dict(self) -> dict:
        errors_list = []
        for e in self.errors:
            if hasattr(e, "to_dict"):
                errors_list.append(e.to_dict())
            elif isinstance(e, dict):
                errors_list.append(e)
            else:
                errors_list.append(
                    {
                        "code": getattr(e, "code", None),
                        "message_key": getattr(e, "message_key", None),
                        "field": getattr(e, "field", None),
                        "params": getattr(e, "params", None),
                    }
                )

        return {"success": self.success, "data": self.data, "errors": errors_list}

    def __iter__(self):
        status = getattr(self, "status", 200)
        return iter((status, self.to_dict()))

    @classmethod
    def from_crud_result(cls, result: CRUDResult) -> "APIResponse":
        """Фабричный метод создания APIResponse из CRUDResult."""
        # Превращаем CRUDError в словари заранее, чтобы избежать проблем с сериализацией
        serialized_errors = [
            {
                "code": err.code,
                "message_key": err.message_key,
                "field": err.field,
                "params": err.params,
            }
            for err in (result.errors or [])
        ]
        return cls(
            success=result.success,
            data=result.data,
            errors=serialized_errors,
            operation=getattr(result, "operation", None),
        )


def map_crud_error_to_status_code(error_code: str) -> int:
    """Определяет HTTP статус-код ошибки на основе кода CRUDError."""
    mapping = {
        "VALIDATION_ERROR": 422,
        "NOT_FOUND": 404,
        "PERSISTENCE_ERROR": 500,
        "BAD_REQUEST": 400,
    }
    return mapping.get(error_code, 400)


def map_crud_result_to_http_status(result: CRUDResult) -> int:
    """Определяет итоговый HTTP статус-код для CRUDResult."""
    if result.success:
        if getattr(result, "operation", None) == "create":
            return 201
        return 200

    if result.errors:
        first_error_code = result.errors[0].code
        return map_crud_error_to_status_code(first_error_code)

    return 500
