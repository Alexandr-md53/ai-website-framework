"""
Unified AI Service Facade for AI Website Framework.
"""

from typing import Dict, Any

from framework.ai.providers.openrouter import OpenRouterProvider
from framework.core.exceptions import AIServiceError


class AIService:
    """
    Главный сервис-фасад для генерации контента через AI.
    Сайт обращается ТОЛЬКО к этому классу.
    """

    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self._provider = self._init_provider()

    def _init_provider(self):
        provider_name = self.settings.get("AI_PROVIDER", "openrouter").lower()
        api_key = self.settings.get("OPENROUTER_API_KEY") or self.settings.get(
            "AI_API_KEY"
        )

        if provider_name == "openrouter":
            default_model = self.settings.get("AI_MODEL", "openai/gpt-4o-mini")
            return OpenRouterProvider(api_key=api_key, default_model=default_model)

        # Сюда в будущем легко добавятся if provider_name == "openai" или "gemini"

        raise AIServiceError(f"Неподдерживаемый AI-провайдер: {provider_name}")

    def generate(
        self, prompt: str, system_prompt: str = "", options: Dict[str, Any] = None
    ) -> str:
        """
        Универсальный метод генерации текста.
        """
        return self._provider.generate_text(
            prompt, system_prompt=system_prompt, options=options
        )
