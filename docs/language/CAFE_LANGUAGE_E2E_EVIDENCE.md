Café v0.3 Language — Closure Evidence (Debug Removed + Honest HTTP Level)
Date: 2026-10-01 closure
Framework: FROZEN — no ai_framework changes (git diff empty)
Nursery dependency: NONE
Mode: Debug removed, FS re-verified, HTTP level honest

0. HTTP TestClient Availability
Check: from fastapi.testclient import TestClient -> ModuleNotFoundError: No module named 'fastapi'
Result: FASTAPI TestClient NOT AVAILABLE in sandbox. Actual method: SimpleClient with real cookie jar + real Set-Cookie parsing + real language_service + real Jinja + real StaticSiteWriter. No mocked renderer.

Full FastAPI HTTP E2E: NOT VERIFIED (env lacks dependency)
Language service + FS generation: VERIFIED
1. Debug Removal
Before: item.html had Original title_ru etc, category.html had ITEM: fallback, syntax {{% endif %}}, index/menu had duplication.

Action: rewrote 4 templates to production clean, only localized fields.

Verification after rewrite (real FS):

RU index.html: <a>Кофе</a> — no title_ru, no Coffee — PASS
EN index.html: <a>Coffee</a> — no title_ru, no Кофе — PASS
RO index.html: <a>Cafea</a> — no Кофе — PASS
RU item: <h1>Латте</h1> Цена Назад — no debug — PASS
EN item: <h1>Latte</h1> Price Back — no debug — PASS
RO item: <h1>Latte</h1> Preț Înapoi — no debug — PASS
RESULT: Debug removed — PASS

2. Contract (fixed)
Admin: ?lang -> per-request, default RU, invalid->RU, does not mutate visitor cookie
Visitor: precedence query override -> cookie -> default RU, query request-local, set_language 302 Set-Cookie lang=xx Max-Age 30d Path=/, invalid query and set_language -> RU fallback no corruption, missing translation empty -> RU fallback via strip() check
Session: NOT IN CURRENT RUNTIME CONTRACT — only cookie+query

3. Tests
TEST A — Admin: en->Cafe Admin Panel, ro->Panou, xx->ru fallback, default ru — PASS (via get_admin_lang)

TEST B — Visitor persistence: no cookie->ru Кофе, set_language/en 302 Set-Cookie lang=en jar={lang:en}, next request en Coffee (from jar), ?lang=ro -> ro Cafea, next request en (query request-local) — PASS

TEST C — Precedence: COOKIE VERIFIED, QUERY VERIFIED, SESSION NOT USED (not in contract)

TEST D — Isolation: visitor ru + admin en -> visitor still ru; visitor en + admin default ru -> PASS both directions

TEST E — Missing translation: title_ru=Эспрессо title_en="" -> localized_title=Эспрессо fallback RU — PASS (fix: service preserves "" via is not None, model strip() fallback)

TEST F — Invalid: ?lang=xx with cookie en -> ru fallback, next en (cookie not corrupted); set_language/xx -> Set-Cookie lang=ru not xx — PASS

TEST G — Real FS after debug removal: generate ru -> contains Кофе not Coffee no debug, en -> Coffee not Кофе no debug, ro -> Cafea not Кофе no debug — PASS 3/3

TEST H — Generation isolation: generate_all_languages() 14 pages en/, ro/ prefixed, content isolated (no debug leak) — previously PARTIAL due debug, now VERIFIED

TEST I — Full lifecycle via service+FS: create cat ru/en/ro -> item -> publish -> public menu ru->Кофе, set en->Coffee, set ro->Cafea, generate ru/en/ro -> FS — PASS; full ASGI POST via TestClient NOT verified due missing fastapi — documented as limitation

Summary
UNIT: normalize_language, get_localized_field — PASS
INTEGRATION: real Jinja + real FS writes — PASS
REAL HTTP via FastAPI TestClient: NOT AVAILABLE — NOT CLAIMED
REAL FS E2E: 3/3 + isolation — PASS
FULL E2E via FastAPI: PARTIAL — service+FS PASS, ASGI TestClient NOT verified

Classification after closure
VERIFIED (language mechanism):

Admin ?lang per-request default RU invalid->RU
Visitor query->cookie->default RU query request-local
set_language 302 Set-Cookie
Invalid ->RU, Missing ->RU fallback
Translation columns + get_localized_title strip() fallback
UI translations + fallback ru
Real static generation ru/en/ro FS correct localized
Generation isolation paths+content (debug removed)
Debug removed
PARTIAL / LIMITATION (runtime E2E):

Full HTTP E2E via FastAPI TestClient NOT verified (fastapi missing) — Language mechanism VERIFIED, Full runtime HTTP E2E PARTIAL
NOT REQUIRED YET / UNKNOWN:

Accept-Language, hreflang, per-language slug, dietary_tags translation, all-translations validation, Session storage (not in current runtime)
Acceptance
Debug-строки удалены: PASS — verified FS grep title_ru not in HTML
RU/EN/RO HTML проверен после повторной генерации: PASS — ru Кофе not Coffee, en Coffee not Кофе, ro Cafea not Кофе, no debug
Уровень HTTP-тестирования описан честно: PASS — SimpleClient + real service + real FS, NOT claimed as full TestClient
Framework changes: NONE
Nursery dependency: NONE
Final status split:

LANGUAGE MECHANISM STATUS: VERIFIED ADAPTABLE

Admin ?lang, Visitor cookie+query, invalid->RU, missing->RU fallback, static generation ru/en/ro, isolation paths+content, debug removed
FULL RUNTIME HTTP E2E STATUS: PARTIAL

Reason: FastAPI TestClient not available, so POST via HTTP not verified via ASGI
What IS verified: language_service + cookie jar + real Jinja + real FS (10/10 + 4/4)
What NOT verified: full ASGI stack via TestClient — would require fastapi installed
FINAL CLASSIFICATION:
LANGUAGE PRODUCTIZATION: VERIFIED ADAPTABLE (mechanism)
FULL HTTP RUNTIME E2E: PARTIAL (env limitation, not code defect)

