from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ValidationContext:
    metadata_provider: Optional[Any] = None
    persistence_provider: Optional[Any] = None
    localization_provider: Optional[Any] = None
    tenant_id: Optional[str] = None
    locale: Optional[str] = "en"
