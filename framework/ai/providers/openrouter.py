"""
OpenRouter AI Provider Implementation.
"""

import requests
from typing import Dict, Any

from framework.ai.providers.base import BaseAIProvider
from framework.core.exceptions import AIServiceError


class OpenRouterProvider(BaseAIProvider):
    """
    Провайдер для работы с API OpenRouter.
    """

    def __init__(self, api_key: str, default_model: str = "openai/gpt-4o-mini"):
        if not api_key:
            raise AIServiceError("Не задан API-ключ для OpenRouter.")
        self.api_key = api_key
        self.default_model = default_model
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    def generate_text(
        self, prompt: str, system_prompt: str = "", options: Dict[str, Any] = None
    ) -> str:
        options = options or {}
        model = options.get("model", self.default_model)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": options.get("temperature", 0.7),
        }

        try:
            response = requests.post(
                self.api_url, json=payload, headers=headers, timeout=60
            )
            response_data = response.json()
        except Exception as err:
            raise AIServiceError(f"Ошибка обращения к OpenRouter API: {err}") from err

        if response.status_code != 200 or "choices" not in response_data:
            error_msg = response_data.get("error", {}).get(
                "message", "Неизвестная ошибка OpenRouter."
            )
            raise AIServiceError(f"OpenRouter вернул ошибку: {error_msg}")

        return response_data["choices"][0]["message"]["content"].strip()
