"""Block 2b / 2b-FIX storefront: category cards, clients' shots, why-cards.

The home page no longer shows the product showcase: the catalogue lives on
``/catalog``. Sections on the home page are: hero → categories → clients'
shots → why choose us → footer.
"""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from showcases.videoshop.security.admin import AdminConfig, hash_password
from showcases.videoshop.web.app import PACKAGED_MEDIA_DIR, create_app
from showcases.videoshop.web.i18n import UI

PASSWORD = "block2b-pass"
CSRF_RE = re.compile(r'name="csrf" value="([^"]+)"')

PORTFOLIO = ("portfolio-city.webp", "portfolio-bloom.webp", "portfolio-street.webp", "portfolio-window.webp")
ANCHORS = ("dealer", "warranty", "delivery", "payment")


@pytest.fixture
def paths(tmp_path):
    (tmp_path / "db").mkdir()
    (tmp_path / "backups").mkdir()
    return {
        "db_path": str(tmp_path / "db" / "shop.sqlite"),
        "backup_dir": str(tmp_path / "backups"),
        "images_dir": str(tmp_path / "images"),
    }


@pytest.fixture
def client(paths):
    admin = AdminConfig(
        username="owner", password_hash=hash_password(PASSWORD, iterations=1000), secret_key=b"b2b"
    )
    return TestClient(create_app(**paths, admin_config=admin, seed_demo=True), follow_redirects=False)


# --- category cards -------------------------------------------------------


def test_category_cards_are_single_clickable_photo_cards(client):
    home = client.get("/").text
    assert "cat-card__img" in home
    assert "cat-card__overlay" in home
    assert "cat-card__title" in home
    assert "cat-card__body" not in home
    assert "cat-card__arrow" not in home
    assert "linear-gradient(to top,rgba(11,21,48,.94)" in home
    assert ".cat-card:hover{transform:scale(1.02)" in home


# --- FIX 1: no product showcase on the home page --------------------------


def test_home_page_has_no_product_showcase(client):
    home = client.get("/").text
    assert 'class="card-p"' not in home
    assert UI["ru"]["featured"] not in home
    assert UI["ru"]["all_products"] not in home
    # the catalogue itself still renders the product cards
    assert 'class="card-p"' in client.get("/catalog").text


# --- FIX 2: clients' shots heading --------------------------------------


def test_clients_shots_heading_and_subtitle(client):
    home = client.get("/").text
    assert UI["ru"]["works_title"] in home
    assert UI["ru"]["works_sub"] in home
    assert 'class="section__title"' in home
    assert 'class="section__sub"' in home
    assert ".section__sub{font-size:16px;color:var(--text-muted)" in home
    assert "--text-muted:#6B7280" in home
    # the four portfolio cards are unchanged
    assert home.count('class="project"') == 4
    positions = [home.index(f"portfolio-{stem}.webp") for stem in ("city", "bloom", "street", "window")]
    assert positions == sorted(positions)
    assert "object-position: center 40%" in home
    assert "aspect-ratio:3/4" in home


# --- FIX 3: why choose us (5 cards) ------------------------------------


def test_why_block_has_five_cards_with_accent_first(client):
    home = client.get("/").text
    assert UI["ru"]["why_title"] in home
    assert UI["ru"]["why_sub"] in home
    assert home.count('class="about-card__icon"') == 5
    assert home.count('class="about-card about-card--main"') == 1
    main_start = home.index('class="about-card about-card--main"')
    main_block = home[main_start : main_start + 1400]
    assert UI["ru"]["why_1_cta"] in main_block
    assert UI["ru"]["why_1_title"] in main_block
    # cobalt icons for the four secondary cards
    assert ".about-card__icon{display:grid;place-items:center;width:44px;height:44px" in home
    assert "var(--cobalt-tint)" in home and "--cobalt:#0047AB" in home
    # hover and focus states
    assert ".about-card:hover{border-color:var(--gold);transform:translateY(-4px)" in home
    assert ".about-card:focus-visible{outline:2px solid var(--gold)" in home
    # responsive breakpoints from the spec
    assert "@media(max-width:1000px)" in home and "@media(max-width:560px)" in home


def test_why_cards_link_to_about_anchors(client):
    home = client.get("/").text
    for anchor in ANCHORS:
        assert f"/page/about?lang=ru#{anchor}" in home, anchor
    # the accent card has no dead URL: href="#" (TODO is a template comment)
    assert 'class="about-card about-card--main" href="#"' in home


def test_about_stub_page_provides_the_anchors(client):
    stub = client.get("/page/about")
    assert stub.status_code == 200
    for anchor in ANCHORS:
        assert f'id="{anchor}"' in stub.text, anchor
    assert client.get("/page/missing").status_code == 404


def test_about_stub_is_replaced_by_a_real_page(paths):
    admin = AdminConfig(
        username="owner", password_hash=hash_password(PASSWORD, iterations=1000), secret_key=b"b2b-real"
    )
    with TestClient(create_app(**paths, admin_config=admin), follow_redirects=False) as c:
        c.post("/admin/login", data={"username": "owner", "password": PASSWORD})
        csrf = CSRF_RE.search(c.get("/admin").text).group(1)
        c.post(
            "/admin/pages/new",
            data={"csrf": csrf, "slug": "about", "title_ru": "О магазине", "body_ru": "Наш текст", "is_published": "1"},
        )
        page = c.get("/page/about")
        assert page.status_code == 200
        assert "Наш текст" in page.text
        assert 'id="dealer"' not in page.text


# --- portfolio media ----------------------------------------------------


def test_portfolio_webp_files_are_optimised_and_served(client):
    for name in PORTFOLIO:
        path = PACKAGED_MEDIA_DIR / "portfolio" / name
        assert path.is_file(), name
        assert path.stat().st_size < 150 * 1024, (name, path.stat().st_size)
        assert client.get(f"/media/portfolio/{name}").status_code == 200
    assert client.get("/media/portfolio/missing.webp").status_code == 404
    assert client.get("/media/portfolio/..%2Fhero.jpg").status_code == 404


def test_home_keeps_placeholder_fallback(client):
    home = client.get("/").text
    assert "/media/placeholder.jpg" in home
    assert "onerror" in home


# --- i18n ---------------------------------------------------------------


def test_new_i18n_keys_exist_in_every_language():
    keys = ("works_title", "works_sub", "why_title", "why_sub", "why_1_title", "why_1_text",
            "why_1_cta", "why_2_title", "why_2_text", "why_3_title", "why_3_text",
            "why_4_title", "why_4_text", "why_5_title", "why_5_text",
            "about_dealer", "about_warranty", "about_delivery", "about_payment")
    for lang in ("ru", "ro", "en"):
        for key in keys:
            assert UI[lang].get(key), (lang, key)
    # translated, not copied from one language to another
    assert len({UI[lang]["works_title"] for lang in ("ru", "ro", "en")}) == 3
