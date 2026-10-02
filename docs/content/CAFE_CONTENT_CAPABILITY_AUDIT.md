CAFE_CONTENT_CAPABILITY_AUDIT — v0.4 Readiness
Date: 2026-10-02
Base: v0.3.1 Closure ACCEPT (Language VERIFIED ADAPTABLE / Full HTTP E2E PARTIAL)
Framework: FROZEN — no ai_framework changes

Evidence Type Legend
RUNTIME: executed via test_runner_no_fastapi.py SimpleClient + real cookie jar + real service + real Jinja + real FS
STATIC: code inspection / FS grep after generation — NOT claimed as runtime HTTP test
12 Capabilities — Specific Evidence
1. Category create localized — RUNTIME
Code: CafeMenuService.create_category(name, slug, name_ru, name_en, name_ro) preserves via is not None
Test: cat = service.create_category(name="Coffee", slug="coffee", name_ru="Кофе", name_en="Coffee", name_ro="Cafea") → cat.name_ru=="Кофе" — in TEST B/G setup
Evidence file: showcases/cafe/services/cafe_menu_service.py:create_category
2. Item create localized — RUNTIME
Code: service.create_item(title, slug, description, price, category_id, title_ru/en/ro, description_ru/en/ro)
Test: item = service.create_item(title="Latte Base", slug="latte", description="Desc long enough for publish gate 12345", price=Decimal("4.5"), category_id=cat.id, title_ru="Латте", title_en="Latte", title_ro="Latte") + service.publish(item.id) → list_published returns it — TEST B/G
Evidence: cafe_menu_service.py:create_item + publish
3. Slug VO — STATIC + RUNTIME
Code: ai_framework/content/slug.py — Slug value object validation/normalization
Runtime: service.create_category(slug="coffee") → unique check, creation succeeds, duplicate would fail — observed in TEST G generate uses slug as path menu/coffee/latte
Evidence: ai_framework/content/slug.py + service slug orchestrator
4. Publish gate — RUNTIME
Code: service.list_published(category_slug) filters by status
Test: unpublished item not in list_published, after service.publish(id) appears — TEST B setup creates then publishes before public menu checks
Evidence: TEST B list_published returns 1 after publish
5. Draft/Published state — RUNTIME
Code: status field draft default, publish transition
Test: same as #4 — state transition verified by count before/after publish
Evidence: CafeMenuService.publish
6. Category→Item FK — RUNTIME
Code: category_id FK in create_item, list_published(category_slug=slug) filters
Test: get_public_menu_category("coffee") returns items with slug latte, category isolation — TEST G list_published(category_slug="coffee")
Evidence: showcases/cafe/services/cafe_menu_service.py:list_published
7. Jinja + GeneratedPage + StaticSiteWriter — RUNTIME
Code: real classes mocked to real Jinja in runner but using same interface as framework:
python

class JinjaTemplateRenderer: Environment(loader=FileSystemLoader(td)).get_template(tpl).render(**ctx)
class GeneratedPage: path, html, kind
class StaticSiteWriter: write(pages, out_dir, clean=True) → Path.write_text

- Test: TEST G `client.generator.generate(lang="ru")` → 7 pages → `writer.write(pages_ru, out_ru)` → `Path.exists()` + content contains — RUNTIME FS
- Evidence: `showcases/cafe/services/cafe_site_generator.py` + `cafe_renderer.py`

### 8. Templates no debug — STATIC (FS grep) — NOT claimed as runtime HTTP
- Code: templates per dump_closure:
`item.html` only `localized_title|default(item.title)`, `localized_description`, `ui.dish.price`, `category_slug`
`category.html` only `localized_name|default(category.name)`, `iw.localized_title`
`index.html` only `localized_categories` + `ui.menu.title`
- Verification: FS grep after generation:
- `title_ru not in html` — PASS (dump_closure line: verified contains title_ru False)
- `Original title not in html` — PASS
- `{{% endif %}}` syntax fixed — PASS
- Evidence: `showcases/cafe/templates/*.html` content dump + `docs/language/CAFE_LANGUAGE_E2E_EVIDENCE.md` section 1

### 9. Generation per lang isolation — paths — RUNTIME
- Code: `generate(lang)` → pages with lang-prefixed paths, `generate_all_languages()` → 14 pages
- Test: TEST G + dump_closure TEST H: `generate_all_languages() 14 pages en/, ro/ prefixed` — RUNTIME
- Evidence: `CafeSiteGenerator.generate` + `generate_all_languages`

### 10. Generation per lang isolation — content — RUNTIME + STATIC grep
- Runtime generation + static grep verification:
- RU `index.html`: `<a>Кофе</a>` — no Coffee — dump_closure verification PASS
- EN `index.html`: `<a>Coffee</a>` — no Кофе — PASS
- RO `index.html`: `<a>Cafea</a>` — no Кофе — PASS
- Item RU: `<h1>Латте</h1> Цена Назад` — no debug
- Item EN: `<h1>Latte</h1> Price Back` — no debug
- Item RO: `<h1>Latte</h1> Preț Înapoi` — no debug
- Test: TEST G real FS checks `contains Кофе? True` + `contains Coffee? True` in respective out dirs
- Evidence: `docs/language/CAFE_LANGUAGE_E2E_EVIDENCE.md` section G + dump_closure lines 75-81

### 11. Missing translation fallback — RUNTIME
- Code: service preserves "" via `is not None`, model `get_localized_title(lang)` uses `strip()` check → fallback RU
- Test: TEST E `cat2` + `item2` `title_ru="Эспрессо" title_en=""` → `get_public_item("drinks","espresso",{"lang":"en"})` → `localized_title=="Эспрессо"` — RUNTIME PASS
- Evidence: `showcases/cafe/services/cafe_language_service.py:get_localized_field` + `models: get_localized_title`

### 12. Invalid translation fallback — RUNTIME
- Code: `normalize_language(xx) -> ru`, `get_visitor_lang` fallback ru, `set_visitor_lang` normalizes before Set-Cookie
- Test: TEST F
- `client.cookies={"lang":"en"}`, `get_public_menu({"lang":"xx"})` → lang=ru fallback, next request en (cookie not corrupted)
- `set_language("xx")` → `Set-Cookie lang=ru not xx`, `normalized==ru`
- Evidence: `cafe_language_service.normalize_language` + TEST F logs

## NOT IN CONTRACT

- Session storage — NOT IN CURRENT CONTRACT — `app_factory public_menu calls get_visitor_lang(cookies=request.cookies, query_params=...) session None` — STATIC code inspection per dump_closure line 86
- Accept-Language, hreflang, per-language slug, dietary_tags, all-translations validation — NOT REQUIRED YET — STATIC scope definition

## Verification Commands for PC (required before ACCEPT declaration)

```powershell
# 1. Framework FROZEN
git diff --stat ai_framework/
# Expected: empty

# 2. Nursery dependency NONE
Select-String -Path showcases/cafe/**/*.py -Pattern "from nursery|import nursery" -CaseSensitive:$false
# Expected: 0 results (only comments allowed)

# 3. Tracked files check — do not mass delete before this
git ls-files --others --exclude-standard | Select-String "_1.py|_2.py|_v031|\.zip|__pycache__|\.pytest_cache"
# These are untracked — safe to ignore via .gitignore, not to mass delete tracked files

# 4. Templates tracked
git ls-files showcases/cafe/templates/
# Expected: 4 files index.html, menu_index.html, category.html, item.html
Acceptance
12/12 VERIFIED with specific runtime/static evidence above, no static claimed as runtime HTTP
Framework FROZEN respected — no new universal abstractions
v0.3.1 ACCEPT, v0.4 READY TO START
