import pathlib


def test_contact_structure():
    from showcases.cafe.content.cafe_info import CAFE_CONTACT

    assert isinstance(CAFE_CONTACT, dict)
    for key in ["phone", "map_url"]:
        assert key in CAFE_CONTACT
    for key in ["address_ru", "address_en", "hours_ru", "hours_en"]:
        assert key in CAFE_CONTACT


def test_contact_optional_render():
    # None values should not break render
    from showcases.cafe.product_app import render_page

    html_ru = render_page("index", "ru")["html"]
    html_en = render_page("about", "en")["html"]
    assert "Café Aurora" in html_ru or "Café" in html_ru
    assert "<footer" in html_ru.lower()


def test_logo_in_header():
    from showcases.cafe.product_app import render_page

    html = render_page("index", "ru")["html"]
    assert "/assets/logo/logo.png" in html
    assert "alt=" in html
    assert "logo" in html.lower()


def test_interior_on_about():
    from showcases.cafe.product_app import render_page

    html = render_page("about", "ru")["html"]
    assert "/assets/interior/interior_01.png" in html
    assert (
        "Interior" in html
        or "интерьер" in html.lower()
        or "interior" in html.lower()
        or "interior" in html
    )


def test_interior_on_index():
    from showcases.cafe.product_app import render_page

    html = render_page("index", "ru")["html"]
    assert "/assets/interior/interior_01.png" in html


def test_footer_exists_ru_en():
    from showcases.cafe.product_app import render_page

    for lang in ["ru", "en"]:
        for page in ["index", "menu", "about"]:
            html = render_page(page, lang)["html"]
            assert "<footer" in html.lower()
            assert "site-footer" in html


def test_og_image():
    from showcases.cafe.product_app import render_page

    html = render_page("index", "ru")["html"]
    assert 'property="og:image"' in html
    assert "/assets/logo/logo.png" in html


def test_no_framework_changes_still_green():
    # This replicates v0.5 guard
    import pathlib

    fw = pathlib.Path("ai_framework")
    if not fw.exists():
        return
    for py in fw.rglob("*.py"):
        if "tools" in str(py) and "make_dumps" in str(py):
            # should not exist after cleanup
            assert False, f"Forbidden file still exists: {py}"
        txt = py.read_text(encoding="utf-8", errors="ignore")
        assert "cafe_info" not in txt.lower() or "cafe_info" not in txt
