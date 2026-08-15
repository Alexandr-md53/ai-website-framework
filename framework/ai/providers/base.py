"""
Base AI Provider Interface for AI Website Framework.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseAIProvider(ABC):
    """
    Абстрактный класс (контракт) для всех AI-провайдеров.
    Каждый новый провайдер (OpenAI, Gemini, OpenRouter) обязан следовать этим правилам.
    """

    @abstractmethod
    def generate_text(
        self, prompt: str, system_prompt: str = "", options: Dict[str, Any] = None
    ) -> str:
        """
        Основной метод для генерации текста по промпту.
        """
        pass
