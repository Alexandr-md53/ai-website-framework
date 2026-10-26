"""V1.2: the language switcher keeps the query and replaces only ``lang``."""
from __future__ import annotations

import html as html_module
import re
from urllib.parse import parse_qsl, urlsplit

from fastapi.testclient import TestClient

from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.web.app import create_app


def _app(tmp_path):
    (tmp_path / "db").mkdir(exist_ok=True)
    (tmp_path / "backups").mkdir(exist_ok=True)
    return create_app(
        db_path=str(tmp_path / "db" / "shop.sqlite"),
        backup_dir=str(tmp_path / "backups"),
        images_dir=str(tmp_path / "images"),
        admin_config=AdminConfig(
            username="owner",
            password_hash=hash_password("x", iterations=1000),
            secret_key=b"c",
        ),
    )


def _client(tmp_path):
    return TestClient(_app(tmp_path), follow_redirects=False)


def _links(response):
    """code -> href for every anchor inside the header language switcher."""
    markup = html_module.unescape(response.text)
    block = re.search(r'<div class="langs">(.*?)</div>', markup, re.S)
    assert block is not None, "language switcher block not found"
    pairs = re.findall(r'<a [^>]*href="([^"]+)"[^>]*>([a-z]{2})</a>', block.group(1))
    return {code: href for href, code in pairs}


def _query(href):
    parts = urlsplit(href)
    return parts.path, parse_qsl(parts.query, keep_blank_values=True)


def _lang_values(pairs):
    return [value for key, value in pairs if key == "lang"]


def test_switcher_keeps_scenario_and_budget(tmp_path):
    page = _client(tmp_path).get("/consultant?scenario=vlog&budget=100000&lang=ru")
    assert page.status_code == 200

    links = _links(page)
    for code in ("ru", "ro", "en"):
        path, pairs = _query(links[code])
        assert path == "/consultant"
        assert ("scenario", "vlog") in pairs
        assert ("budget", "100000") in pairs
        assert _lang_values(pairs) == [code]


def test_switcher_adds_lang_when_absent(tmp_path):
    page = _client(tmp_path).get("/consultant?scenario=interview&budget=300000")
    assert page.status_code == 200

    links = _links(page)
    for code in ("ru", "ro", "en"):
        path, pairs = _query(links[code])
        assert path == "/consultant"
        assert ("scenario", "interview") in pairs
        assert ("budget", "300000") in pairs
        assert _lang_values(pairs) == [code]


def test_switcher_without_query(tmp_path):
    page = _client(tmp_path).get("/")
    assert page.status_code == 200

    links = _links(page)
    for code in ("ru", "ro", "en"):
        path, pairs = _query(links[code])
        assert path == "/"
        assert pairs == [("lang", code)]


def test_switcher_keeps_repeated_have_parameters(tmp_path):
    page = _client(tmp_path).get(
        "/consultant?scenario=interview&have=cameras&have=microphones&lang=ru"
    )
    assert page.status_code == 200

    links = _links(page)
    for code in ("ru", "ro", "en"):
        _path, pairs = _query(links[code])
        assert [value for key, value in pairs if key == "have"] == [
            "cameras",
            "microphones",
        ]
        assert _lang_values(pairs) == [code]


def test_lang_is_replaced_not_duplicated(tmp_path):
    page = _client(tmp_path).get("/consultant?scenario=vlog&lang=ro&budget=100000")
    assert page.status_code == 200

    for code, href in _links(page).items():
        _path, pairs = _query(href)
        assert len([key for key, _value in pairs if key == "lang"]) == 1
        assert _lang_values(pairs) == [code]


def test_reverse_language_transitions_keep_state(tmp_path):
    client = _client(tmp_path)
    page = client.get("/consultant?scenario=wedding&budget=300000&have=tripods&lang=en")
    assert page.status_code == 200

    for code in ("ro", "ru", "en"):
        href = _links(page)[code]
        path, pairs = _query(href)
        assert path == "/consultant"
        assert ("scenario", "wedding") in pairs
        assert ("budget", "300000") in pairs
        assert ("have", "tripods") in pairs
        assert _lang_values(pairs) == [code]

        page = client.get(href)
        assert page.status_code == 200


def test_admin_login_switcher_still_renders(tmp_path):
    page = _client(tmp_path).get("/admin/login")
    assert page.status_code == 200

    links = _links(page)
    assert links, "admin switcher must be present"
    for _code, href in links.items():
        path, pairs = _query(href)
        assert path == "/admin/login"
        assert len([key for key, _value in pairs if key == "lang"]) == 1
