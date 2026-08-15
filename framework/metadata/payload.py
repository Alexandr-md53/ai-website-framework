"""
Publication Payload Data Class for AI Website Framework.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class PublicationPayload:
    """
    Универсальный контейнер данных для публикаций.
    Приводит любые внешние данные к единому стандарту фреймворка.
    """

    title: str
    text: str
    id: Optional[str] = None
    image: Optional[str] = None
    image_required: bool = False
    buttons: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует payload в словарь для передачи в плагины и генераторы.
        """
        return {
            "id": self.id,
            "title": self.title,
            "text": self.text,
            "image": self.image,
            "image_required": self.image_required,
            "buttons": self.buttons,
            "metadata": self.metadata,
        }
