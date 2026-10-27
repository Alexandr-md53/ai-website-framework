"""Stage 3: formatter pure functions (escaping, limits, split integrity)."""
from __future__ import annotations

from showcases.videoshop.publishers.telegram_formatter import (
    CAPTION_LIMIT,
    TEXT_LIMIT,
    caption,
    escape_html,
    prepare_messages,
    split_escaped,
)


def test_formatter_escaping():
    escaped = escape_html('<script>alert("x")</script> & more')
    assert "<" not in escaped
    assert ">" not in escaped
    assert escaped == "&lt;script&gt;alert(\"x\")&lt;/script&gt; &amp; more"


def test_formatter_limits():
    parts = prepare_messages("hello")
    assert parts == ["hello"]
    assert len(parts[0]) <= TEXT_LIMIT == 4096
    assert len(caption("x" * 2000)) <= CAPTION_LIMIT == 1024


def test_formatter_split_integrity():
    text = ("paragraph " + "x" * 200 + "\n\n") * 60
    assert len(text) > 12000

    escaped = escape_html(text)
    parts = prepare_messages(text)

    assert parts
    assert all(0 < len(part) <= TEXT_LIMIT for part in parts)
    assert "".join(parts) == escaped
    assert split_escaped(escaped) == parts


def test_formatter_split_prefers_paragraph():
    text = "a" * 3000 + "\n\n" + "b" * 3000
    parts = prepare_messages(text)
    assert parts[0] == "a" * 3000 + "\n\n"
    assert parts[1] == "b" * 3000
    assert "".join(parts) == text
