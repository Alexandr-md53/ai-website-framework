"""Stage 3: Telegram adapter behaviour with an injected fake transport."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import pytest

from showcases.videoshop.domain.catalog import ValidationError
from showcases.videoshop.domain.publications import Channel
from showcases.videoshop.infrastructure.telegram_http import (
    TelegramTimeout,
    TelegramTransportError,
)
from showcases.videoshop.publishers import registry
from showcases.videoshop.publishers.telegram import TelegramAdapter

ENV_NAME = "VIDEOSHOP_TELEGRAM_MAIN_BOT_TOKEN"
STAMP = "2026-01-01T00:00:00+00:00"
PUBLISHERS_DIR = Path(__file__).resolve().parents[1] / "publishers"


def _channel(
    *,
    channel_key: str = "main",
    credentials_ref: str = "MAIN",
    settings_json: str = '{"chat_id": "123456789"}',
    platform: str = "telegram",
) -> Channel:
    return Channel(
        id=None,
        platform=platform,
        channel_key=channel_key,
        name="Main",
        credentials_ref=credentials_ref,
        settings_json=settings_json,
        default_language="",
        timezone="Europe/Chisinau",
        is_active=True,
        created_at=STAMP,
        updated_at=STAMP,
    )


class RecordingTransport:
    def __init__(self, *responses) -> None:
        self._responses = list(responses)
        self.calls = []

    def __call__(self, method, payload, *, token, timeout):
        self.calls.append(
            {
                "method": method,
                "payload": dict(payload),
                "token": token,
                "timeout": timeout,
            }
        )
        response = self._responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def _adapter(transport, *, env=None, timeout=15.0) -> TelegramAdapter:
    if env is None:
        env = {ENV_NAME: "test-token"}
    return TelegramAdapter(transport=transport, timeout=timeout, env=env)


def test_send_message_ok():
    transport = RecordingTransport((200, {"ok": True, "result": {"message_id": 55}}))
    result = _adapter(transport).send(_channel(), "<b>hi</b>")

    assert result.ok is True
    assert result.external_id == "55"
    assert result.retryable is False
    assert result.retry_after is None
    assert len(transport.calls) == 1
    call = transport.calls[0]
    assert call["method"] == "sendMessage"
    assert call["payload"]["chat_id"] == "123456789"
    assert call["payload"]["parse_mode"] == "HTML"
    assert call["payload"]["disable_web_page_preview"] is True
    assert call["payload"]["text"] == "&lt;b&gt;hi&lt;/b&gt;"
    assert call["timeout"] == 15.0


@pytest.mark.parametrize(
    "payload, expected",
    [
        ({"ok": False, "parameters": {"retry_after": 120}}, 120),
        ({"ok": False, "parameters": {"retry_after": 0}}, None),
        ({"ok": False, "parameters": {"retry_after": "120"}}, None),
        ({"ok": False}, None),
        ({"ok": False, "parameters": {}}, None),
    ],
)
def test_send_429_retry_after(payload, expected):
    transport = RecordingTransport((429, payload))
    result = _adapter(transport).send(_channel(), "hello")

    assert result.ok is False
    assert result.retryable is True
    assert result.retry_after == expected


@pytest.mark.parametrize("status", [500, 502, 503])
def test_send_5xx_retryable(status):
    transport = RecordingTransport((status, {}))
    result = _adapter(transport).send(_channel(), "hello")

    assert result.ok is False
    assert result.retryable is True
    assert result.retry_after is None
    assert result.error == f"telegram {status}"


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_send_4xx_not_retryable(status):
    transport = RecordingTransport((status, {}))
    result = _adapter(transport).send(_channel(), "hello")

    assert result.ok is False
    assert result.retryable is False
    assert result.error == f"telegram {status}"


def test_send_408_retryable_ambiguous():
    transport = RecordingTransport((408, {}))
    result = _adapter(transport).send(_channel(), "hello")

    assert result.ok is False
    assert result.retryable is True
    assert result.retry_after is None
    assert result.external_id is None
    assert "ambiguous" in (result.error or "")


def test_timeout_retryable():
    transport = RecordingTransport(TelegramTimeout("t"))
    result = _adapter(transport).send(_channel(), "hello")

    assert result.ok is False
    assert result.retryable is True
    assert result.retry_after is None


def test_transport_error_retryable():
    transport = RecordingTransport(TelegramTransportError("boom"))
    result = _adapter(transport).send(_channel(), "hello")

    assert result.ok is False
    assert result.retryable is True


def test_missing_credentials_fails_closed():
    transport = RecordingTransport()
    empty_env = _adapter(transport, env={})
    result = empty_env.send(_channel(credentials_ref="MAIN"), "hello")

    assert result.ok is False
    assert result.retryable is False
    assert result.error == f"credentials env missing: {ENV_NAME}"
    assert transport.calls == []

    for credentials_ref in ("", "bad ref!"):
        result = _adapter(transport).send(_channel(credentials_ref=credentials_ref), "hi")
        assert result.ok is False
        assert result.retryable is False
        assert result.error == "credentials_ref invalid"
    assert transport.calls == []


@pytest.mark.parametrize(
    "settings_json, expected",
    [
        ("{}", "chat_id missing/invalid"),
        ("not-json", "settings_json invalid"),
        ('{"chat_id": ""}', "chat_id missing/invalid"),
        ('{"chat_id": 123}', "chat_id missing/invalid"),
        ('{"chat_id": null}', "chat_id missing/invalid"),
    ],
)
def test_missing_chat_id_fails_closed(settings_json, expected):
    transport = RecordingTransport()
    result = _adapter(transport).send(_channel(settings_json=settings_json), "hello")

    assert result.ok is False
    assert result.retryable is False
    assert result.error == expected
    assert transport.calls == []


def test_no_fallback_to_channel_key():
    transport = RecordingTransport()
    env = {"VIDEOSHOP_TELEGRAM_MAIN_BOT_TOKEN": "token-from-channel-key"}
    result = _adapter(transport, env=env).send(
        _channel(channel_key="main", credentials_ref=""), "hello"
    )

    assert result.ok is False
    assert result.retryable is False
    assert result.error == "credentials_ref invalid"
    assert transport.calls == []


def test_no_token_in_logs(caplog):
    sentinel = "S3CRET-TOKEN-xyz"
    caplog.set_level(logging.DEBUG)
    transport = RecordingTransport((200, {"ok": True, "result": {"message_id": 1}}))

    result = _adapter(transport, env={ENV_NAME: sentinel}).send(_channel(), "hello")

    assert result.ok is True
    assert sentinel not in caplog.text
    assert "api.telegram.org" not in caplog.text


def test_adapter_does_not_touch_db():
    forbidden = (
        "publications_store",
        "sqlite_provider",
        "services.publications",
        "import sqlite3",
    )
    sources = sorted(PUBLISHERS_DIR.glob("*.py"))
    assert sources
    combined = "\n".join(path.read_text(encoding="utf-8") for path in sources)
    for marker in forbidden:
        assert marker not in combined, f"publishers must not use {marker!r}"


def test_registry_get_adapter():
    adapter = registry.get_adapter("telegram")
    assert isinstance(adapter, TelegramAdapter)
    assert adapter.platform == "telegram"
    assert adapter.capabilities.supports_html is True
    assert adapter.capabilities.max_text_len == 4096
    assert adapter.capabilities.max_caption_len == 1024

    with pytest.raises(ValidationError):
        registry.get_adapter("website")


def test_media_not_supported_in_s1():
    transport = RecordingTransport()
    result = _adapter(transport).send(_channel(), "hello", media=object())

    assert result.ok is False
    assert result.retryable is False
    assert result.error == "media not supported in S1"
    assert transport.calls == []


@pytest.mark.parametrize("chat_id", ["-1001234567890", "123456789", "-42"])
def test_chat_id_from_settings_json(chat_id):
    transport = RecordingTransport((200, {"ok": True, "result": {"message_id": 7}}))
    result = _adapter(transport).send(
        _channel(settings_json=json.dumps({"chat_id": chat_id})), "hello"
    )

    assert result.ok is True
    assert transport.calls[0]["payload"]["chat_id"] == chat_id


def test_long_message_fails_without_send():
    transport = RecordingTransport()
    result = _adapter(transport).send(_channel(), "x" * 5000)

    assert result.ok is False
    assert result.retryable is False
    assert result.error == "message too long for single-part send in S1"
    assert transport.calls == []


@pytest.mark.parametrize("response", [(200, "not-a-json"), (200, {"ok": True})])
def test_invalid_json_response_not_success(response):
    transport = RecordingTransport(response)
    result = _adapter(transport).send(_channel(), "hello")

    assert result.ok is False
    assert result.retryable is False
    assert result.error == "telegram response invalid"
    assert result.external_id is None
