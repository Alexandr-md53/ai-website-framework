"""
Metadata Builder & Transformer for AI Website Framework.
"""

from typing import Dict, Any
from framework.metadata.payload import PublicationPayload
from framework.core.exceptions import ValidationError


class MetadataBuilder:
    """
    Конвертер и валидатор метаданных.
    Принимает сырые данные из любого источника и строит из них PublicationPayload.
    """

    @staticmethod
    def build_from_dict(data: Dict[str, Any]) -> PublicationPayload:
        """
        Создает объект PublicationPayload из словаря сырых данных.
        """
        if not isinstance(data, dict):
            raise ValidationError("Исходные данные метаданных должны быть словарем.")

        title = data.get("title", "").strip()
        text = data.get("text", "").strip()

        if not title and not text:
            raise ValidationError(
                "Публикация должна содержать хотя бы заголовок или текст."
            )

        return PublicationPayload(
            id=data.get("id"),
            title=title,
            text=text,
            image=data.get("image"),
            image_required=data.get("image_required", False),
            buttons=data.get("buttons", []),
            metadata=data.get("metadata", {}),
        )
