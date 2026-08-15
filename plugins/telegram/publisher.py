"""
Telegram Publisher Plugin for AI Website Framework.
"""

from pathlib import Path
import json
import requests

from framework.core.contracts import PublisherPluginContract
from framework.core.exceptions import PluginExecutionError, ValidationError


class TelegramPublisherPlugin(PublisherPluginContract):
    """
    Плагин отправки публикаций в Telegram.
    """

    def get_metadata(self) -> dict:
        return {
            "id": "telegram",
            "title": "Telegram",
            "description": "Publishes content to Telegram channels.",
            "icon": "✈️",
            "version": "1.0.0",
            "category": "social",
            "supports_images": True,
            "supports_buttons": True,
            "supports_html": True,
        }

    def validate(self, publication: dict) -> bool:
        if not isinstance(publication, dict):
            raise ValidationError("Публикация должна быть словарем.")

        message = self._build_message(publication)
        if not message.strip():
            raise ValidationError("Публикация не может быть пустой.")

        image_path = publication.get("image")
        if publication.get("image_required", False) and not image_path:
            raise ValidationError("Отсутствует обязательное изображение.")

        if image_path and not Path(image_path).exists():
            raise ValidationError(f"Файл изображения не найден: {image_path}")

        return True

    def publish(self, publication: dict, settings: dict) -> bool:
        # 1. Проверяем валидность
        self.validate(publication)

        # 2. Берем настройки из Settings фреймворка
        token = settings.get("TELEGRAM_BOT_TOKEN")
        chat_id = settings.get("TELEGRAM_CHAT_ID")

        if not token or not chat_id:
            raise PluginExecutionError(
                "Не заданы TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID в Settings."
            )

        # 3. Формируем сообщение и кнопки
        message = self._build_message(publication)
        keyboard = self._build_keyboard(publication)
        image_path = publication.get("image")

        payload = {
            "chat_id": chat_id,
            "caption": message,
            "parse_mode": "HTML",
        }
        if keyboard:
            payload["reply_markup"] = json.dumps(keyboard)

        # 4. Отправляем в Telegram
        if image_path:
            return self._send_photo(token, payload, Path(image_path))

        return self._send_text(token, chat_id, message, keyboard)

    # --- Вспомогательные методы (твоя логика из Питомника) ---

    def _build_message(self, publication: dict) -> str:
        title = publication.get("title", "")
        text = publication.get("text", "")
        parts = []
        if title:
            parts.append(f"<b>{title}</b>")
        if text and text.strip() != title.strip():
            parts.append(text)
        return "\n\n".join(parts)

    def _build_keyboard(self, publication: dict) -> dict | None:
        buttons = publication.get("buttons", [])
        rows = []
        for btn in buttons:
            if btn.get("text") and btn.get("url"):
                rows.append([{"text": btn["text"], "url": btn["url"]}])
        return {"inline_keyboard": rows} if rows else None

    def _send_photo(self, token: str, payload: dict, image_path: Path) -> bool:
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        try:
            with open(image_path, "rb") as img:
                res = requests.post(
                    url,
                    data=payload,
                    files={"photo": (image_path.name, img)},
                    timeout=15,
                )
            return self._process_response(res)
        except Exception as err:
            raise PluginExecutionError(
                f"Ошибка отправки фото в Telegram: {err}"
            ) from err

    def _send_text(
        self, token: str, chat_id: str, message: str, keyboard: dict = None
    ) -> bool:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        if keyboard:
            payload["reply_markup"] = json.dumps(keyboard)
        try:
            res = requests.post(url, data=payload, timeout=15)
            return self._process_response(res)
        except Exception as err:
            raise PluginExecutionError(
                f"Ошибка отправки текста в Telegram: {err}"
            ) from err

    def _process_response(self, response) -> bool:
        try:
            data = response.json()
        except Exception as err:
            raise PluginExecutionError("Telegram вернул некорректный JSON.") from err

        if data.get("ok"):
            return True
        raise PluginExecutionError(data.get("description", "Ошибка Telegram API."))
