def test_nav_present():
    from showcases.cafe.product_app import render_page

    for page in ["index", "menu", "about"]:
        for lang in ["ru", "en"]:
            html = render_page(page, lang)["html"].lower()
            assert "<nav>" in html, f"nav missing {page} {lang}"
            assert "href=" in html
            assert "150 mdl" in html.lower()


def test_lang_switch():
    from showcases.cafe.product_app import render_page

    html_ru = render_page("index", "ru")["html"]
    html_en = render_page("index", "en")["html"]
    assert "/en/" in html_ru or "/en" in html_ru
    assert "/ru" in html_en or "/" in html_en


def test_structure():
    from showcases.cafe.product_app import render_page

    for page in ["index", "menu", "about"]:
        for lang in ["ru", "en"]:
            data = render_page(page, lang)
            assert data["title"]
            assert data["description"]
            assert "lang=" in data["html"]
            assert "<header>" in data["html"].lower() or "<nav>" in data["html"].lower()
