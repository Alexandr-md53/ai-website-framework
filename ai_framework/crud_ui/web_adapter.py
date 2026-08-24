import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict
from uuid import UUID


def _json_serializer(obj: Any) -> Any:
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


class WebResponseAdapter:
    def to_context(self, view_model: Any) -> Dict[str, Any]:
        if is_dataclass(view_model):
            return asdict(view_model)
        if hasattr(view_model, "dict") and callable(view_model.dict):
            return view_model.dict()
        return dict(view_model)

    def to_json(self, view_model: Any) -> str:
        context = self.to_context(view_model)
        return json.dumps(context, default=_json_serializer)
