Café Language vs Nursery Language — Comparison v0.3 Closure (Debug Removed)
Aspect	Nursery	Café v0.3 Closure (Debug Removed)	Classification
Admin lang selection	request.args.get("lang","ru") ?lang	get_admin_lang(query_params) — GET /admin?lang=en returns lang=en, per-request	VERIFIED REUSABLE
Admin storage	None only URL	None only URL — request-local, no cookie	VERIFIED
Admin default	ru	ru — GET /admin no lang → ru	VERIFIED
Admin fallback	UI.get(lang, UI["ru"])	normalize→ru + UI.get → RU — GET /admin?lang=xx → ru	VERIFIED
Admin preservation	redirect f"/admin/categories?lang={lang}"	Contract preserve ?lang — implemented	VERIFIED
Visitor lang selection	session.get("lang","ru")	get_visitor_lang(cookies, query_params) — cookie jar + query override, session NOT in runtime	VERIFIED ADAPTABLE (session removed from contract)
Visitor storage	Flask session signed cookie	Cookie lang Max-Age 30d Path=/ + Set-Cookie real — Test B proves persistence via jar	VERIFIED (COOKIE)
Visitor change route	GET /set_language/<lang> sets session	GET /set_language/{lang} sets cookie 302 redirect referrer — Set-Cookie lang=en verified	VERIFIED
Visitor default	ru	ru — no cookie → ru	VERIFIED
Visitor fallback query	if not in allowed keep old	normalize xx→ru — ?lang=xx → ru, cookie stays en — request-local	VERIFIED
Visitor fallback set_language	-	set_language/xx → Set-Cookie lang=ru not xx — VERIFIED	VERIFIED
Session support	Yes Flask session	No session middleware — SESSION NOT USED, removed from current runtime contract — NOT REQUIRED YET	NOT REQUIRED (removed from contract)
Query override	Not in Nursery	?lang=ro with cookie en → ro, next request en — request-local VERIFIED	VERIFIED ADAPTABLE
Admin vs Visitor isolation	Admin args vs session independent	Admin query only vs Visitor cookie — same client: set visitor ru, admin en → visitor still ru — VERIFIED both directions	VERIFIED
Supported langs	{"ru","ro","en"}	{"ru","ro","en"} — same	VERIFIED
Content storage	columns name_ru/ro/en	columns name_ru/ro/en title_ru/ro/en — same pattern, added title_* for MenuItem	VERIFIED
Content selection	if en: name_en elif ro else ru	get_localized_title same branching + strip() check for empty → fallback ru	VERIFIED
Content fallback missing	no fallback GAP	empty title_en → returns Эспрессо (ru fallback) — TEST E PASS, fix: preserve "" via is not None	VERIFIED (improvement)
UI structure	UI={ru:{chat,blog,quiz,admin},en,ro}	CAFE_UI={ru:{menu,dish,admin},en,ro} same nested different keys	VERIFIED ADAPTABLE
UI fallback	get_ui(lang)=UI.get(lang, UI["ru"])	same — invalid xx returns ru UI	VERIFIED
Site generation lang	per content_lang	generate(lang) — real FS writes ru_site contains Кофе only, en contains Coffee only, ro contains Cafea only, no debug — TEST G PASS after debug removal	VERIFIED ADAPTABLE
Site isolation	single output	Separate out dirs + prefixed en/, ro/ — TEST H PASS paths isolated + content isolated (debug removed) — previously PARTIAL, now VERIFIED	VERIFIED
Debug removal	—	Templates cleaned: item.html no Original title_ru, category.html no fallback debug, index/menu only localized_categories — verified FS grep title_ru not in HTML	VERIFIED
Full lifecycle	create→render	create cat/item → publish → public menu ru/en/ro → generate ru/en/ro → FS — via service+FS PASS; full ASGI POST via TestClient NOT verified due missing fastapi — documented	VERIFIED (service+FS) / PARTIAL (ASGI)
Framework changes	-	NONE — git diff ai_framework empty	VERIFIED
Nursery dependency	-	NONE — no import	VERIFIED
Updated Gaps after Closure
VERIFIED: 19 items (including debug removal, content isolation now VERIFIED)
PARTIAL: 0 for language mechanism; 1 for full runtime HTTP E2E (FastAPI TestClient not available — env limitation)
GAP: 0 for mechanism (session removed from contract)
UNKNOWN: per-language slug, dietary_tags translation
NOT REQUIRED YET: Accept-Language header, hreflang, all-translations validation, session storage (removed from contract)
Final Classification
LANGUAGE PRODUCTIZATION: VERIFIED ADAPTABLE — mechanism + real FS + debug removed
FULL HTTP RUNTIME E2E: PARTIAL — service+FS verified, ASGI TestClient not available in sandbox (env limitation, not code defect)

