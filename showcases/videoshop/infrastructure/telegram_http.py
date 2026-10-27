"""Minimal stdlib Telegram HTTP transport (no logging, no retries).

``send_request`` performs exactly one POST and maps transport failures to two
exception types.  It never logs the URL, the token or the response body: the URL
contains the token and must not leak into logs or error messages.
"""
from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from typing import Any, Dict, Mapping, Tuple

API_BASE = "https://api.telegram.org"


class TelegramTransportError(RuntimeError):
    """Network failure that is not a timeout (retryable at the runner level)."""


class TelegramTimeout(TelegramTransportError):
    """The request timed out; the outcome is ambiguous."""


def _parse_json(body: bytes) -> Dict[str, Any]:
    try:
        decoded = body.decode("utf-8")
    except UnicodeDecodeError:
        return {}
    try:
        data = json.loads(decoded or "{}")
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def send_request(
    method: str,
    payload: Mapping[str, Any],
    *,
    token: str,
    timeout: float = 15.0,
) -> Tuple[int, Dict[str, Any]]:
    """One POST to ``https://api.telegram.org/bot<token>/<method>``.

    Returns ``(status_code, parsed_json)``; HTTP errors keep their code and body.
    Raises :class:`TelegramTimeout` / :class:`TelegramTransportError` for
    network failures.  No token, URL or body is ever logged here.
    """
    url = f"{API_BASE}/bot{token}/{method}"
    body = json.dumps(dict(payload)).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status), _parse_json(response.read())
    except urllib.error.HTTPError as error:
        return int(error.code), _parse_json(error.read())
    except urllib.error.URLError as error:
        reason = getattr(error, "reason", None)
        if isinstance(reason, (socket.timeout, TimeoutError)):
            raise TelegramTimeout("telegram request timed out") from error
        raise TelegramTransportError("telegram transport error") from error
    except (socket.timeout, TimeoutError) as error:
        raise TelegramTimeout("telegram request timed out") from error
