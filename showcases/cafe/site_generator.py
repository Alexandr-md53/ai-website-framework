from pathlib import Path
import sys, shutil

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from showcases.cafe.product_app import (
    render_page,
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    get_complete_languages,
    CAFE_BASE_URL,
)

DIST = Path("dist/cafe_site")
ASSETS_SRC = Path(__file__).parent / "assets"
ASSETS_DST = DIST / "assets"


def generate():
    out = DIST
    out.mkdir(parents=True, exist_ok=True)
    langs = sorted(SUPPORTED_LANGUAGES)
    print(
        f"[v0.9.1] SUPPORTED={langs} DEFAULT={DEFAULT_LANGUAGE} BASE_URL={CAFE_BASE_URL or 'NOT SET'}"
    )
    for lang in langs:
        (out / lang).mkdir(exist_ok=True)
    if ASSETS_SRC.exists():
        if ASSETS_DST.exists():
            shutil.rmtree(ASSETS_DST)
        shutil.copytree(ASSETS_SRC, ASSETS_DST)
        print("[assets] copied")
    for lang in langs:
        for page in ["index", "menu", "about"]:
            data = render_page(page, lang)
            fname = "index.html" if page == "index" else f"{page}.html"
            (out / lang / fname).write_text(data["html"], encoding="utf-8")
            print(f" - {lang}/{fname} complete={data['is_complete']}")
    # A. Root canonical fix: no canonical when BASE_URL not set
    if CAFE_BASE_URL:
        redirect_canonical = f'<link rel="canonical" href="{CAFE_BASE_URL.rstrip("/")}/{DEFAULT_LANGUAGE}/">'
    else:
        redirect_canonical = (
            "<!-- canonical NOT READY FOR PRODUCTION — CAFE_BASE_URL not set -->"
        )
    redirect_html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Redirect to /'
        + DEFAULT_LANGUAGE
        + '/</title><meta http-equiv="refresh" content="0; url=/'
        + DEFAULT_LANGUAGE
        + '/">'
        + redirect_canonical
        + '</head><body><p>Redirecting to <a href="/'
        + DEFAULT_LANGUAGE
        + '/">/'
        + DEFAULT_LANGUAGE
        + "/</a></p><!-- REDIRECT CONTRACT: HTML meta refresh fallback; HTTP 302 NOT IMPLEMENTED - requires hosting config --><!-- REDIRECT CONTRACT: HTTP 302 / -> /"
        + DEFAULT_LANGUAGE
        + "/ --></body></html>"
    )
    (out / "index.html").write_text(redirect_html, encoding="utf-8")
    Path(".tmp").mkdir(exist_ok=True)
    Path(".tmp/REDIRECT_CONTRACT.md").write_text(
        f"# Redirect Contract v0.9.1\nHTML fallback: PROVEN (meta refresh)\nHTTP 302: NOT IMPLEMENTED (requires hosting platform config)\nActual HTTP redirect: UNKNOWN until hosting selected\nRequired: HTTP 302 / -> /{DEFAULT_LANGUAGE}/\nDEFAULT={DEFAULT_LANGUAGE}\nSUPPORTED={langs}\n",
        encoding="utf-8",
    )
    comp = get_complete_languages()
    print(f"[sitemap] complete={comp}")
    if CAFE_BASE_URL:
        base = CAFE_BASE_URL.rstrip("/")
        urls = []
        for lang in comp:
            urls.append(f"{base}/{lang}/")
            urls.append(f"{base}/{lang}/menu.html")
            urls.append(f"{base}/{lang}/about.html")
        sitemap = (
            '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + "".join([f"<url><loc>{u}</loc></url>" for u in urls])
            + "</urlset>"
        )
        (out / "sitemap.xml").write_text(sitemap, encoding="utf-8")
        if (out / "sitemap.draft.xml").exists():
            (out / "sitemap.draft.xml").unlink()
    else:
        draft_urls = []
        for lang in comp:
            draft_urls.append(f"/{lang}/")
            draft_urls.append(f"/{lang}/menu.html")
            draft_urls.append(f"/{lang}/about.html")
        draft = (
            "<!-- NOT READY FOR PRODUCTION — CAFE_BASE_URL not set -->\n<urlset>"
            + "".join([f"<url><loc>{u}</loc></url>" for u in draft_urls])
            + "</urlset>"
        )
        (out / "sitemap.draft.xml").write_text(draft, encoding="utf-8")
        if (out / "sitemap.xml").exists():
            (out / "sitemap.xml").unlink()
        print("[sitemap] draft only")
    print(f"[v0.9.1] Generated to {out.resolve()}")
    return out


if __name__ == "__main__":
    generate()
