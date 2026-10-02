CONSUMER_CAFE_CAPABILITY_MATRIX.md — v0.3.1 Language Closure — Debug Removed + Honest HTTP Level
Consumer: Café
Framework: FROZEN — ai_framework unchanged, git diff empty
Nursery dependency: NONE — no import
Current: v0.3.1 Closure — Debug removed, content isolation VERIFIED, HTTP level documented honestly

Capability Matrix
Capability	Café Evidence (v0.3.1)	Classification
Slug	validate_slug same regex + _slug_index unique	REUSABLE
Rendering	cafe_renderer wrapper + lang-aware localized_title — production templates only localized_* — debug removed — VERIFIED	REUSABLE + ADAPTABLE
SEO	_make_seo uses localized title per lang — production templates no raw translations	REUSABLE
GeneratedPage	generate(lang) sorted + sitemap, generate_all_languages() prefixed en/, ro/ — after debug removal EN file does NOT contain RU	ADAPTABLE
StaticSiteWriter	writer.write() + real filesystem files exist + no debug leak — VERIFIED	REUSABLE
Stock/Order	stock_quantity + lifecycle	CAFÉ-SPECIFIC
Media	cafe_image_service showcase-local variants 500x350/1000x700 — VERIFIED	REUSABLE pattern + ADAPTABLE
Language Admin	get_admin_lang(query_params) — GET /admin?lang=en → en Cafe Admin Panel, xx→ru fallback, default ru — 4/4 PASS — service-level with real query_params semantics	VERIFIED REUSABLE
Language Visitor	get_visitor_lang(cookies, query_params) query override → cookie → default ru + set_language 302 Set-Cookie — cookie jar persistence EN from Set-Cookie, query override request-local, invalid xx→ru — 10/10 PASS	VERIFIED ADAPTABLE
Language Precedence	Contract: query override → cookie → default RU (session not in contract). SESSION NOT USED IN CAFÉ RUNTIME — NOT IN CONTRACT	NOT IN CURRENT CONTRACT
Admin/Visitor Isolation	Same client: visitor ru, admin en → visitor still ru — PASS both directions	VERIFIED
Translation Model	title_ru/ro/en description_ru/ro/en + get_localized_title fallback ru→base — missing en empty → ru fallback PASS, production templates only localized_*	VERIFIED
UI Translations	CAFE_UI nested + get_ui() fallback — per lang — PASS	VERIFIED ADAPTABLE
Static Generation Language	generate(lang=ru) → ru_site/index.html contains Кофе only (no Coffee, no title_ru), en contains Coffee only (no Кофе), ro contains Cafea only — after debug removal — PASS real filesystem	VERIFIED ADAPTABLE
Generation Isolation	Separate out dirs ru_site/en_site/ro_site + prefixed en/, ro/ — 14 pages — paths isolated + content isolation VERIFIED after debug removal (EN does NOT contain RU)	VERIFIED
Debug Output Removal	Production templates cleaned: item.html only localized_title/description, category.html only items_with_images localized_title, index/menu_index only localized_categories[].localized_name — verified contains title_ru False, Original title False — PASS	VERIFIED
Full Lifecycle	POST categories → POST items → publish → GET visitor RU/EN/RO → POST /site/generate → filesystem — PASS	VERIFIED
HTTP TestClient Availability	fastapi not installed (ModuleNotFoundError) — REAL HTTP via TestClient NOT AVAILABLE — documented honestly, not claimed. Actual: Service + Renderer + StaticSiteWriter + real cookie jar + filesystem	UNKNOWN / NOT AVAILABLE — honest
Closure v0.3.1 Summary
Debug removed: templates now only localized_title/description/name — verified no title_ru string, no Original title, EN does NOT contain RU
Re-generated RU/EN/RO verified: RU contains Кофе only, EN Coffee only, RO Cafea only — isolated
HTTP level honest: TestClient NOT AVAILABLE (fastapi not installed) — actual tested Service-level + real cookie jar + real filesystem — VERIFIED, not claimed as full HTTP E2E
Contract fixed: Admin ?lang → default RU per-request, Visitor query override → cookie → default RU, Invalid → RU, Missing → RU fallback, Session not in contract
Framework NONE, Nursery NONE
Final split status:

LANGUAGE MECHANISM: VERIFIED ADAPTABLE
LANGUAGE PRODUCTIZATION (filesystem): VERIFIED ADAPTABLE (debug removed, content isolated)
FULL HTTP E2E via TestClient: UNKNOWN / NOT AVAILABLE — honest
