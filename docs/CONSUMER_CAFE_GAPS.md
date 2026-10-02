CONSUMER_CAFE_GAPS.md — v0.3.1 Closure — Debug Removed + Honest HTTP Level
Consumer: Café
Framework: FROZEN
Previous: v0.3 with debug leak PARTIAL
Current: v0.3.1 Closure — Debug removed, content isolation VERIFIED, HTTP level honest

Resolved
Debug leak title_ru/en/ro in templates → RESOLVED VERIFIED (production templates only localized_*, re-generated RU EN RO no leak, EN does NOT contain RU, verified contains title_ru False)
Content isolation → RESOLVED VERIFIED (previously PARTIAL due debug, now VERIFIED — RU Кофе only, EN Coffee only, RO Cafea only)
Admin ?lang, Visitor cookie persistence, query override, isolation, invalid, missing fallback, filesystem — all VERIFIED
Remaining Gaps (honest v0.3.1)
Gap	Classification	Reason	Required?
Full HTTP E2E via FastAPI TestClient	UNKNOWN / NOT AVAILABLE	fastapi not installed in sandbox (ModuleNotFoundError) — REAL HTTP via TestClient NOT AVAILABLE — documented honestly, not claimed as VERIFIED. Actual tested: Service + Renderer + StaticSiteWriter + real cookie jar with Set-Cookie semantics + real filesystem — VERIFIED	NOT REQUIRED — can be upgraded when fastapi available without code change
Session storage	NOT IN CURRENT CONTRACT	Contract v0.3.1: Admin ?lang → default RU per-request, Visitor query override → cookie → default RU, Invalid → RU, Missing → RU fallback, Session not in contract. app_factory public_menu calls get_visitor_lang(cookies=request.cookies, query_params=...) session None, no Flask session middleware.	NOT IN CONTRACT
Accept-Language header	NOT REQUIRED YET	Not in Nursery, not in current scope	NOT REQUIRED YET
hreflang SEO alternates	NOT REQUIRED YET	No alternates in generated pages, not in Nursery	NOT REQUIRED YET
per-language slug	UNKNOWN	Slug unique global, not per lang	UNKNOWN
dietary_tags translation	UNKNOWN	Not required	UNKNOWN / NOT REQUIRED YET
all-translations validation	NOT REQUIRED YET	Allows optional translations with fallback	NOT REQUIRED YET
Media Gaps unchanged
Framework ImageService primitive — GAP intentional FROZEN — NOT REQUIRED — showcase-local correct
MIME, size/dimension, atomic replacement, DB/FS consistency, orphan cleanup — GAP / NOT REQUIRED YET
Acceptance v0.3.1
Debug-строки удалены — VERIFIED (contains title_ru False, Original title False, verified in re-generated files)
RU/EN/RO HTML проверен после повторной генерации — VERIFIED (RU Кофе only, EN Coffee only, RO Cafea only, no cross leak, no debug)
Уровень HTTP-тестирования описан честно — TestClient NOT AVAILABLE (fastapi not installed), Service + cookie jar + filesystem VERIFIED, not claimed as full HTTP E2E
Framework changes: NONE — git diff ai_framework empty
Nursery dependency: NONE — no import
Контракт зафиксирован: Admin ?lang → default RU per-request, Visitor query override → cookie → default RU, Invalid → RU, Missing → RU fallback, Session not in contract — VERIFIED
Финальный статус разделён: LANGUAGE MECHANISM VERIFIED ADAPTABLE, FULL RUNTIME E2E PARTIAL (honest) due to TestClient not available — not upgraded PARTIAL to VERIFIED without evidence
Files
docs/language/CAFE_LANGUAGE_E2E_EVIDENCE.md — closure v0.3.1 debug removed + honest HTTP level + final split status + regeneration logs
docs/language/CAFE_LANGUAGE_COMPARISON.md — v0.3.1 comparison
docs/CONSUMER_CAFE_CAPABILITY_MATRIX.md — v0.3.1 matrix
docs/CONSUMER_CAFE_GAPS.md — this file
showcases/cafe/templates/index.html, menu_index.html, category.html, item.html — production cleaned, no raw title_ru/en/ro
