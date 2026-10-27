"""Telegram adapter: one message per publication, no retries, no database.

Fail-closed order (each step happens before any HTTP request):

1. ``media is not None`` -> media is not supported in S1;
2. invalid ``credentials_ref`` -> ``credentials_ref invalid``;
3. missing bot-token env var -> ``credentials env missing: <ENV_NAME>`` (name only);
4. invalid/missing ``chat_id`` in ``settings_json`` -> ``settings_json invalid`` or
   ``chat_id missing/invalid``;
5. escaped text longer than 4096 -> ``message too long for single-part send in S1``.

Only after that the injected transport is called exactly once.  The adapter maps
Telegram answers to :class:`PublishResult` and never retries - the runner (stage 4)
owns the retry policy.
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Mapping, Optional

from ..domain.catalog import ValidationError
from ..domain.publications import (
    Channel,
    PublishResult,
    credentials_env_name,
    validate_credentials_ref,
)
from ..infrastructure.telegram_http import (
    TelegramTimeout,
    TelegramTransportError,
    send_request,
)
from .base import AdapterCapabilities
from .telegram_formatter import TEXT_LIMIT, escape_html

Transport = Callable[..., Any]


class TelegramAdapter:
    """Telegram Bot API adapter for text-only publications (S1)."""

    platform = "telegram"
    capabilities = AdapterCapabilities(
        platform="telegram",
        supports_html=True,
        supports_images=False,
        supports_buttons=False,
        max_text_len=TEXT_LIMIT,
        max_caption_len=1024,
    )

    def __init__(
        self,
        *,
        transport: Optional[Transport] = None,
        timeout: float = 15.0,
        env: Optional[Mapping[str, str]] = None,
    ) -> None:
        self._transport = transport or send_request
        self._timeout = float(timeout)
        self._env = env if env is not None else os.environ

    # ----------------------------------------------------------------- helpers
    @staticmethod
    def _read_chat_id(channel: Channel):
        try:
            settings = json.loads(channel.settings_json or "{}")
        except (TypeError, ValueError):
            return None, "settings_json invalid"
        if not isinstance(settings, dict):
            return None, "settings_json invalid"
        value = settings.get("chat_id")
        if not isinstance(value, str) or not value.strip():
            return None, "chat_id missing/invalid"
        return value, None

    def validate(self, channel: Channel, text: str) -> None:
        validate_credentials_ref(channel.credentials_ref)
        _, error = self._read_chat_id(channel)
        if error is not None:
            raise ValidationError(error)
        if not str(text or "").strip():
            raise ValidationError("text is required")

    # -------------------------------------------------------------------- send
    def send(
        self, channel: Channel, text: str, media: Any = None
    ) -> PublishResult:
        if media is not None:
            return PublishResult(False, None, "media not supported in S1", False, None)

        try:
            credentials_ref = validate_credentials_ref(channel.credentials_ref)
        except ValidationError:
            return PublishResult(False, None, "credentials_ref invalid", False, None)

        env_name = credentials_env_name(credentials_ref)
        token = self._env.get(env_name)
        if not token:
            return PublishResult(
                False, None, f"credentials env missing: {env_name}", False, None
            )

        chat_id, chat_error = self._read_chat_id(channel)
        if chat_error is not None:
            return PublishResult(False, None, chat_error, False, None)

        escaped = escape_html(text)
        if not escaped.strip():
            return PublishResult(False, None, "text is required", False, None)
        if len(escaped) > TEXT_LIMIT:
            return PublishResult(
                False,
                None,
                "message too long for single-part send in S1",
                False,
                None,
            )

        payload = {
            "chat_id": chat_id,
            "text": escaped,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            status, body = self._transport(
                "sendMessage", payload, token=token, timeout=self._timeout
            )
        except TelegramTimeout:
            return PublishResult(False, None, "telegram timeout", True, None)
        except TelegramTransportError:
            return PublishResult(False, None, "telegram transport error", True, None)

        return self._map_response(status, body)

    # ------------------------------------------------------------ response map
    @staticmethod
    def _map_response(status: Any, body: Any) -> PublishResult:
        payload = body if isinstance(body, Mapping) else {}
        try:
            code = int(status)
        except (TypeError, ValueError):
            return PublishResult(False, None, "telegram response invalid", False, None)

        if code == 200 and payload.get("ok") is True:
            result = payload.get("result")
            if isinstance(result, Mapping) and result.get("message_id") is not None:
                return PublishResult(True, str(result["message_id"]), None, False, None)
            return PublishResult(False, None, "telegram response invalid", False, None)

        if code == 429:
            retry_after = None
            parameters = payload.get("parameters")
            if isinstance(parameters, Mapping):
                value = parameters.get("retry_after")
                if isinstance(value, int) and not isinstance(value, bool) and value > 0:
                    retry_after = value
            return PublishResult(False, None, "telegram 429", True, retry_after)

        if code == 408:
            return PublishResult(
                False, None, "telegram 408 (outcome ambiguous)", True, None
            )

        if 500 <= code <= 599:
            return PublishResult(False, None, f"telegram {code}", True, None)

        if 400 <= code <= 499:
            return PublishResult(False, None, f"telegram {code}", False, None)

        return PublishResult(False, None, "telegram response invalid", False, None)
