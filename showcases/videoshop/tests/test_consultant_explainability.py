"""Explainable recommendations V1: matched facts, gaps, navigation, budget."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jinja2 import Environment, FileSystemLoader

from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.web.app import _parse_budget_minor, create_app
from showcases.videoshop.web.config import StoreConfig
from showcases.videoshop.web.i18n import get_ui

CONTACT = "shop@example.com"
TEMPLATES = Path(__file__).resolve().parents[1] / "web" / "templates"

LIVE_SLUGS = {
    "cameras": "cameras",
    "lenses": "obektivy",
    "microphones": "mikrofony",
    "lighting": "svet",
    "stabilizers": "stabilizatory",
    "tripods": "shtativy",
}

CATEGORY_NAMES = {
    "cameras": "Cameras",
    "lenses": "Lenses",
    "microphones": "Microphones",
    "lighting": "Lighting",
    "stabilizers": "Stabilizers",
    "tripods": "Tripods",
}

#: the live catalogue: slug, category, price in MDL, English attributes
CATALOGUE = (
    ("canon-eos-r5", "cameras", "129990.00",
     [("Type", "Full Frame"), ("Video", "8K"), ("Stabilization", "IBIS")]),
    ("sony-alpha-a7-iv", "cameras", "89990.00",
     [("Type", "Full Frame"), ("Video", "4K60"), ("Stabilization", "IBIS")]),
    ("canon-rf-24-70mm-f-2-8-l-is-usm", "lenses", "79990.00",
     [("Type", "Zoom"), ("Aperture", "f/2.8"), ("Lens mount", "RF")]),
    ("sony-fe-50mm-f-1-4-gm", "lenses", "44990.00",
     [("Type", "Fix"), ("Aperture", "f/1.4"), ("Lens mount", "FE")]),
    ("rode-lavalier-go", "microphones", "1250.00", [("Type", "Lavalier")]),
    ("sennheiser-mke-600", "microphones", "3450.00", [("Type", "Shotgun")]),
    ("godox-lr150", "lighting", "850.00", [("Color temp", "3200K-5600K")]),
    ("manfrotto-befree-live", "tripods", "3900.00", [("Head", "Fluid head")]),
)


def _app(tmp_path, mode=None):
    (tmp_path / "db").mkdir(exist_ok=True)
    (tmp_path / "backups").mkdir(exist_ok=True)
    app = create_app(
        db_path=str(tmp_path / "db" / "shop.sqlite"),
        backup_dir=str(tmp_path / "backups"),
        images_dir=str(tmp_path / "images"),
        admin_config=AdminConfig(
            username="owner",
            password_hash=hash_password("x", iterations=1000),
            secret_key=b"c",
        ),
        store_config=StoreConfig(mode=mode) if mode else None,
    )
    app.state.catalog.update_settings({"contact_email": CONTACT})
    return app


def _client(tmp_path, mode=None):
    return TestClient(_app(tmp_path, mode=mode), follow_redirects=False)


def _seed(catalog):
    ids = {}
    for key, name in CATEGORY_NAMES.items():
        ids[key] = catalog.create_category(
            slug=LIVE_SLUGS[key], texts={"en": {"name": name}}
        ).id
    for slug, category, price, attributes in CATALOGUE:
        catalog.create_product(
            slug=slug,
            category_id=ids[category],
            price=price,
            currency="MDL",
            texts={"en": {"name": slug.replace("-", " ").title()}},
            attributes=[("en", name, value) for name, value in attributes],
            is_published=True,
        )
    return ids


def _get(client, query):
    response = client.get("/consultant?" + query)
    assert response.status_code == 200, response.status_code
    return response.text


# --- matched facts (only what the engine returned) -----------------------


def test_matched_facts_are_rendered(tmp_path):
    client = _client(tmp_path)
    _seed(client.app.state.catalog)

    html = _get(client, "scenario=interview&budget=300000&lang=en")

    assert "Type: Full Frame" in html
    assert "Aperture: f/1.4" in html
    assert "consultant__facts" in html


def test_facts_include_ignores_empty_values():
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=True)
    template = env.get_template("_consultant_facts.html")

    rendered = template.render(facts=[("Type", "Full Frame"), ("Ghost", "")])
    assert rendered.strip() == "Type: Full Frame"

    empty = template.render(facts=[("Ghost", "")])
    assert empty.strip() == ""


# --- gaps (what the catalogue cannot answer) -----------------------------


def test_sport_gaps_are_rendered(tmp_path):
    client = _client(tmp_path)
    _seed(client.app.state.catalog)

    html = _get(client, "scenario=sport&lang=en")

    assert "Catalogue cannot answer:" in html
    assert "frame rate (FPS)" in html and "autofocus" in html


def test_interview_has_no_gaps_block(tmp_path):
    client = _client(tmp_path)
    _seed(client.app.state.catalog)

    html = _get(client, "scenario=interview&lang=en")

    assert "Catalogue cannot answer:" not in html


# --- navigation ----------------------------------------------------------


def test_nav_link_points_to_the_consultant(tmp_path):
    client = _client(tmp_path)

    html = client.get("/?lang=en").text

    assert 'href="/consultant?lang=en"' in html


@pytest.mark.parametrize("lang", ["ru", "ro", "en"])
def test_nav_link_is_localized(tmp_path, lang):
    from showcases.videoshop.web.i18n import UI

    client = _client(tmp_path)

    html = client.get("/?lang=" + lang).text

    assert ('href="/consultant?lang=%s"' % lang) in html
    assert UI[lang]["nav_consultant"] in html


def test_nav_link_and_route_are_off_without_public_catalog(tmp_path):
    client = _client(tmp_path, mode="visitka")

    html = client.get("/?lang=en").text

    assert "/consultant" not in html
    assert client.get("/consultant?lang=en").status_code == 404


# --- budget parsing ------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("300000", 30_000_000),
        ("300 000", 30_000_000),
        ("300\u00a0000", 30_000_000),
        ("", None),
        ("abc", None),
    ],
)
def test_budget_parser(raw, expected):
    assert _parse_budget_minor(raw) == expected


def test_budget_with_spaces_equals_plain(tmp_path):
    client = _client(tmp_path)
    _seed(client.app.state.catalog)

    plain = _get(client, "scenario=interview&budget=100000&lang=en")
    spaced = _get(client, "scenario=interview&budget=100 000&lang=en")

    assert "Budget is not enough" in plain
    assert "Budget is not enough" in spaced


def test_garbage_budget_is_ignored(tmp_path):
    client = _client(tmp_path)
    _seed(client.app.state.catalog)

    html = _get(client, "scenario=interview&budget=abc&lang=en")

    assert "Budget is not enough" not in html


# --- V1.1 localization ---------------------------------------------------


def _templates():
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=True)
    return env.get_template("_consultant_facts.html"), env.get_template("_consultant_gaps.html")


def _labels(lang):
    consultant = get_ui(lang)["consultant"]
    return consultant["attrs"], consultant["gaps"]


def test_all_languages_share_the_label_keys():
    expected_attrs = {"Type", "Video", "Stabilization", "Aperture", "Color temp", "Head"}
    expected_gaps = {
        "fps",
        "autofocus",
        "iso",
        "weather_sealing",
        "payload_vs_kit_weight",
        "monopod",
    }
    for lang in ("ru", "ro", "en"):
        attrs, gaps = _labels(lang)
        assert set(attrs) == expected_attrs
        assert set(gaps) == expected_gaps
        assert all(value for value in attrs.values())
        assert all(value for value in gaps.values())


@pytest.mark.parametrize(
    "lang,expected",
    [("ru", "Тип: Full Frame"), ("ro", "Tip: Full Frame"), ("en", "Type: Full Frame")],
)
def test_facts_are_localized(lang, expected):
    facts_template, _ = _templates()
    attrs, _gaps = _labels(lang)

    html = facts_template.render(facts=[("Type", "Full Frame")], labels=attrs)

    assert expected in html


@pytest.mark.parametrize(
    "lang,expected",
    [
        ("ru", "частота кадров (FPS)"),
        ("ro", "rata cadrelor (FPS)"),
        ("en", "frame rate (FPS)"),
    ],
)
def test_gaps_are_localized(lang, expected):
    _, gaps_template = _templates()
    _attrs, gaps = _labels(lang)

    html = gaps_template.render(gaps=("fps",), labels=gaps)

    assert expected in html


def test_unknown_keys_fall_back_to_the_raw_names():
    facts_template, gaps_template = _templates()
    attrs, gaps = _labels("ru")

    facts_html = facts_template.render(facts=[("Ghost attr", "X")], labels=attrs)
    gaps_html = gaps_template.render(gaps=("unknown_gap",), labels=gaps)

    assert facts_html.strip() == "Ghost attr: X"
    assert gaps_html.strip() == "unknown_gap"


def test_templates_work_without_a_label_mapping():
    facts_template, gaps_template = _templates()

    assert facts_template.render(facts=[("Type", "Full Frame")]).strip() == "Type: Full Frame"
    assert gaps_template.render(gaps=("fps",)).strip() == "fps"


def test_empty_gaps_render_nothing():
    _, gaps_template = _templates()

    assert gaps_template.render(gaps=(), labels={}).strip() == ""


@pytest.mark.parametrize("lang", ["ru", "ro", "en"])
def test_explanations_are_localized_on_the_page(tmp_path, lang):
    client = _client(tmp_path)
    _seed(client.app.state.catalog)
    attrs, gaps = _labels(lang)

    facts_html = _get(client, "scenario=interview&budget=300000&lang=" + lang)
    gaps_html = _get(client, "scenario=sport&lang=" + lang)

    assert ("%s: Full Frame" % attrs["Type"]) in facts_html
    assert ("%s: f/1.4" % attrs["Aperture"]) in facts_html
    assert ("%s:" % gaps["fps"]) in gaps_html or ("%s" % gaps["fps"]) in gaps_html
    assert "payload_vs_kit_weight" not in gaps_html


def test_facts_keep_their_place_after_the_cards(tmp_path):
    client = _client(tmp_path)
    _seed(client.app.state.catalog)

    html = _get(client, "scenario=interview&budget=300000&lang=ru")

    grid = html.index('class="grid"')
    facts = html.index("consultant__facts")
    total = html.index("Итого")
    assert grid < facts < total


def test_unknown_language_falls_back_to_the_shop_default(tmp_path):
    client = _client(tmp_path)
    _seed(client.app.state.catalog)
    default_lang = client.app.state.catalog.get_settings().default_language
    expected = get_ui(default_lang)["consultant"]["attrs"]["Type"]

    html = _get(client, "scenario=interview&budget=300000&lang=zz")

    assert ("%s: Full Frame" % expected) in html
