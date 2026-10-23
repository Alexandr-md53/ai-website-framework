"""Layer 4 MVP: deterministic consultant, four scenarios, honest outcomes."""
from __future__ import annotations

import re

from fastapi.testclient import TestClient

from showcases.videoshop.domain.consultant import (
    STATUS_FULL,
    STATUS_PARTIAL,
    match_value,
    recommend,
)
from showcases.videoshop.domain.scenarios import (
    CATEGORY_ALIASES,
    CATEGORY_KEYS,
    SCENARIOS_BY_ID,
)
from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.web.app import create_app

CONTACT = "shop@example.com"

#: the live catalogue keeps transliterated slugs, exactly like production
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

#: the real catalogue: slug, category, price in MDL, English attributes
CATALOGUE = (
    ("canon-eos-r5", "cameras", "129990.00",
     [("Sensor", "45 MP"), ("Type", "Full Frame"), ("Video", "8K"), ("Stabilization", "IBIS")]),
    ("sony-alpha-a7-iv", "cameras", "89990.00",
     [("Sensor", "33 MP"), ("Type", "Full Frame"), ("Video", "4K60"), ("Stabilization", "IBIS")]),
    ("canon-rf-24-70mm-f-2-8-l-is-usm", "lenses", "79990.00",
     [("Type", "Zoom"), ("Aperture", "f/2.8"), ("Lens mount", "RF"), ("Stabilization", "IS")]),
    ("sony-fe-50mm-f-1-4-gm", "lenses", "44990.00",
     [("Type", "Fix"), ("Aperture", "f/1.4"), ("Lens mount", "FE"), ("Stabilization", "G Master")]),
    ("rode-lavalier-go", "microphones", "1250.00",
     [("Type", "Lavalier"), ("Pattern", "Omnidirectional"), ("Connector", "3.5 mm TRS"),
      ("Cable length", "1.2 m")]),
    ("sennheiser-mke-600", "microphones", "3450.00",
     [("Type", "Shotgun"), ("Pattern", "Supercardioid"), ("Power", "Battery/Phantom"),
      ("Connector", "XLR")]),
    ("godox-lr150", "lighting", "850.00",
     [("Type", "Ring light"), ("Diameter", "18 inch"), ("Power", "USB"),
      ("Color temp", "3200K-5600K")]),
    ("aputure-amaran-60d", "lighting", "2450.00",
     [("Type", "LED Panel"), ("Power", "60W"), ("Color temp", "5600K"), ("Mount", "Bowens")]),
    ("godox-s-type-80cm", "lighting", "950.00",
     [("Type", "Umbrella softbox"), ("Diameter", "80 cm"), ("Mount", "Bowens"),
      ("Reflector", "Silver")]),
    ("dji-rs-3-mini", "stabilizers", "4800.00",
     [("Type", "3-axis gimbal"), ("Payload", "2 kg"), ("Weight", "795 g"),
      ("Battery life", "up to 10 hours")]),
    ("dji-ronin-s", "stabilizers", "7500.00",
     [("Type", "3-axis gimbal"), ("Payload", "3.6 kg"), ("Weight", "1.8 kg"),
      ("Battery life", "up to 12 hours")]),
    ("shtativ-kf-concept", "tripods", "1450.00",
     [("Type", "Universal"), ("Height", "168 cm"), ("Load capacity", "9 kg"),
      ("Material", "Aluminum"), ("Head", "Ball head")]),
    ("manfrotto-befree-live", "tripods", "3900.00",
     [("Type", "Video tripod"), ("Maximum heigh", "150  sm"), ("Load capacity", "4kg"),
      ("Head", "Fluid head")]),
)


def _app(tmp_path):
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
    )
    app.state.catalog.update_settings({"contact_email": CONTACT})
    return app


def _client(tmp_path):
    return TestClient(_app(tmp_path), follow_redirects=False)


def _seed(catalog):
    ids = {}
    for key, name in CATEGORY_NAMES.items():
        ids[key] = catalog.create_category(
            slug=LIVE_SLUGS[key], texts={"en": {"name": name}}
        ).id
    products = {}
    for slug, category, price, attributes in CATALOGUE:
        products[slug] = catalog.create_product(
            slug=slug,
            category_id=ids[category],
            price=price,
            currency="MDL",
            texts={"en": {"name": slug.replace("-", " ").title()}},
            attributes=[("en", name, value) for name, value in attributes],
            is_published=True,
        )
    return ids, products


def _get(client, query):
    response = client.get("/consultant?" + query)
    assert response.status_code == 200, response.status_code
    return response.text


# --- 1. full kit ---------------------------------------------------------


def test_interview_builds_full_kit_within_budget(tmp_path):
    client = _client(tmp_path)
    _seed(client.app.state.catalog)

    html = _get(client, "scenario=interview&budget=300000")

    assert "140 980 MDL" in html
    assert html.count('class="card-p"') == 8   # 2+2+2+1+1 cards across 5 groups
    assert "mailto:" not in html  # a full kit needs no call to action


# --- 2. sport refused ----------------------------------------------------


def test_sport_is_refused_by_mount(tmp_path):
    client = _client(tmp_path)
    _seed(client.app.state.catalog)

    html = _get(client, "scenario=sport")

    assert "несовместимо по байонету" in html
    assert 'href="mailto:%s"' % CONTACT in html


# --- 3. budget below the minimum ----------------------------------------


def test_budget_below_minimum_is_reported(tmp_path):
    client = _client(tmp_path)
    _seed(client.app.state.catalog)

    html = _get(client, "scenario=interview&budget=100000")

    assert "140 980 MDL" in html
    assert "Не хватает бюджета" in html
    assert 'href="mailto:%s"' % CONTACT in html


# --- 4. sport proxy note -------------------------------------------------


def test_sport_marks_the_fps_proxy(tmp_path):
    client = _client(tmp_path)
    _seed(client.app.state.catalog)

    html = _get(client, "scenario=sport")

    assert "Прокси" in html and "FPS/AF" in html


# --- 5. empty catalogue --------------------------------------------------


def test_empty_catalogue_is_honest(tmp_path):
    client = _client(tmp_path)
    # no products at all
    html = _get(client, "scenario=interview")

    assert "Нет подходящих" in html
    assert 'href="mailto:%s"' % CONTACT in html


# --- 6. owned camera blocks lenses (fail-closed mount) -------------------


def test_owned_camera_blocks_lenses(tmp_path):
    client = _client(tmp_path)
    _seed(client.app.state.catalog)

    html = _get(client, "scenario=interview&have=cameras&budget=300000")

    assert "укажите байонет" in html
    assert "6 000 MDL" in html          # микрофоны + свет + штатив
    assert 'href="mailto:%s"' % CONTACT in html


# --- 7. owned microphone: budget and total apply to the remainder --------


def test_owned_microphone_recomputes_the_total(tmp_path):
    client = _client(tmp_path)
    _seed(client.app.state.catalog)

    html = _get(client, "scenario=interview&have=microphones&budget=300000")

    assert "139 730 MDL" in html
    assert "140 980 MDL" not in html


# --- 8. mount filters the wrong brand ------------------------------------


def test_vlog_offers_only_the_matching_mount(tmp_path):
    client = _client(tmp_path)
    _seed(client.app.state.catalog)

    html = _get(client, "scenario=vlog")

    assert "Sony Alpha A7 Iv" in html or "sony-alpha-a7-iv" in html or "Sony" in html
    assert "Canon Eos R5" not in html and "Canon EOS R5" not in html
    assert "136 230 MDL" in html


# --- 9. numeric normalization (engine) ------------------------------------


def test_aperture_and_weight_normalization():
    assert match_value("Aperture", "f/1.4", "num_le", 2.8)
    assert match_value("Aperture", "f/2.8", "num_le", 2.8)
    assert not match_value("Aperture", "f/4", "num_le", 2.8)
    assert match_value("Payload", "3.6 kg", "num_ge", 3600)
    assert match_value("Weight", "795 g", "num_le", 800)
    assert match_value("Maximum heigh", "150  sm", "num_ge", 150)


# --- 10. video equivalence -------------------------------------------------


def test_video_equivalence_table():
    assert match_value("Video", "8K", "equiv", "gte_4k")
    assert match_value("Video", "4K60", "equiv", "gte_4k")
    assert not match_value("Video", "1080p", "equiv", "gte_4k")
    assert "4K" not in "8K"  # a substring check would silently miss 8K


# --- 11. no invented facts + partial outcome ------------------------------


def test_no_invented_facts_and_partial_outcome(tmp_path):
    app = _app(tmp_path)
    catalog = app.state.catalog
    ids, _ = _seed(catalog)
    products = catalog.list_products(published_only=True)
    scenario = SCENARIOS_BY_ID["interview"]

    result = recommend(products, scenario, category_ids=ids, budget_minor=30_000_000)
    assert result.status == STATUS_FULL
    known = {product.id for product in products}
    for group in result.groups:
        for item in group.items:
            assert item.product.id in known
            pairs = dict(item.product.attributes_for("en"))
            for name, value in item.matched:
                assert pairs.get(name) == value  # every shown fact is stored

    without_light = [p for p in products if p.category_id != ids["lighting"]]
    partial = recommend(without_light, scenario, category_ids=ids, budget_minor=30_000_000)
    assert partial.status == STATUS_PARTIAL
    assert "lighting" in partial.missing_keys
    assert all(group.key != "lighting" for group in partial.groups)


# --- live slugs (regression for the empty-result bug) ----------------------


def test_category_aliases_cover_the_live_slugs(tmp_path):
    app = _app(tmp_path)
    catalog = app.state.catalog
    _seed(catalog)

    live = {category.slug for category in catalog.list_categories()}
    assert live == {"cameras", "obektivy", "mikrofony", "svet", "stabilizatory", "shtativy"}
    for key in CATEGORY_KEYS:
        assert CATEGORY_ALIASES.get(key, key) in live


def test_interview_on_live_slugs_is_full(tmp_path):
    client = _client(tmp_path)
    _seed(client.app.state.catalog)

    html = _get(client, "scenario=interview&budget=300000")

    assert "140 980 MDL" in html
    assert "Нет подходящих" not in html


def test_wedding_on_live_slugs_is_full(tmp_path):
    client = _client(tmp_path)
    _seed(client.app.state.catalog)

    html = _get(client, "scenario=wedding&budget=300000")

    assert "145 780 MDL" in html
    assert "Нет подходящих" not in html


# --- interface language of the result -------------------------------------


def test_consultant_form_keeps_the_language(tmp_path):
    client = _client(tmp_path)
    _seed(client.app.state.catalog)

    for lang, marker in (("ru", 'name="lang" value="ru"'),
                         ("ro", 'name="lang" value="ro"'),
                         ("en", 'name="lang" value="en"')):
        html = _get(client, "lang=" + lang)
        assert marker in html, lang


def test_result_is_russian_on_request(tmp_path):
    client = _client(tmp_path)
    _seed(client.app.state.catalog)

    html = _get(client, "scenario=interview&budget=300000&lang=ru")

    assert 'lang="ru"' in html
    assert "камеры" in html and "Итого" in html


def test_result_is_romanian_on_request(tmp_path):
    client = _client(tmp_path)
    _seed(client.app.state.catalog)

    html = _get(client, "scenario=interview&budget=300000&lang=ro")

    assert 'lang="ro"' in html
    assert "camere" in html and "Total" in html
    assert "камеры" not in html and "Итого" not in html


def test_result_is_english_on_request(tmp_path):
    client = _client(tmp_path)
    _seed(client.app.state.catalog)

    html = _get(client, "scenario=interview&budget=300000&lang=en")

    assert 'lang="en"' in html
    assert "cameras" in html and "Total" in html
    assert "камеры" not in html and "Итого" not in html


def test_sport_refusal_is_romanian(tmp_path):
    client = _client(tmp_path)
    _seed(client.app.state.catalog)

    html = _get(client, "scenario=sport&budget=300000&lang=ro")

    assert "incompatibil la baionetă" in html
    assert "несовместимо" not in html
