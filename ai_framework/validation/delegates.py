from typing import Protocol, Optional, Dict, Any
from ai_framework.validation.types import ValidationSchema


class MetadataProviderProtocol(Protocol):
    """Контракт для получения схем валидации из Metadata Engine."""

    def get_schema(self, entity_name: str) -> Optional[ValidationSchema]: ...


class UniquenessProviderProtocol(Protocol):
    """Контракт для проверки уникальности полей в Persistence Layer."""

    async def is_unique(
        self,
        entity_name: str,
        field_name: str,
        value: Any,
        exclude_id: Optional[Any] = None,
    ) -> bool: ...


class SlugAvailabilityProviderProtocol(Protocol):
    """Контракт для проверки доступности slug в Slug Service."""

    async def is_slug_available(
        self, slug: str, tenant_id: Optional[str] = None
    ) -> bool: ...


class LocalizationProviderProtocol(Protocol):
    """Контракт для интеграции с Localization Engine (опциональный резолвер ключей)."""

    def translate(
        self, message_key: str, locale: str, params: Optional[Dict[str, Any]] = None
    ) -> str: ...
