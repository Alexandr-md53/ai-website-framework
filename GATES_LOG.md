# GATES_LOG — VideoShop

> **Назначение:** краткая хронология этапов и решений. Подробные отчёты — в переписке
> (Worker #2 → владелец); в репозитории хранится только сводка.
> Обновляется после каждого этапа.

## Легенда статусов

- **ACCEPTED** — принято руководителем
- **IMPLEMENTED — NOT ACCEPTED** — реализовано, приёмка не проведена
- **IMPLEMENTED WITH LIMITATIONS** — принято с ограничениями
- **DEFERRED** / **PLANNED** / **BLOCKED**
- **IMPLEMENTED — UNCOMMITTED** — реализовано и покрыто тестами, но не закоммичено

---

## S1 — Транзакционный API

- **Дата:** 2026-10-12
- **Статус:** IMPLEMENTED — NOT ACCEPTED
- **Что:** `VideoShopTransaction`, `BEGIN IMMEDIATE`, commit/rollback, запрет вложенности
- **Файлы:** `infrastructure/sqlite_provider.py`, `tests/test_transaction_api.py` (16)

## S2 — CAS и версии

- **Дата:** 2026-10-12 · **Статус:** ACCEPTED
- **Что:** `update_record_cas`, guards F-1/F-2/F-3, `CasResult`
- **Файлы:** `sqlite_provider.py`, `test_cas_contract.py` (13), `test_versioned_entity_guards.py` (16)

## S3 — Slug registry

- **Дата:** 2026-10-12 · **Статус:** ACCEPTED
- **Что:** уникальность `(entity_type, slug)` через PK, partial unique `(entity_type, entity_id) WHERE state='live'`
- **Файлы:** `slug_registry.py`, `migrations/s3.py`, `test_slug_registry.py` (41),
  `test_live_slug_invariant.py` (9), `test_s3_migrations.py` (5)

## S4 — Entity lifecycle

- **Дата:** 2026-10-13 · **Статус:** ACCEPTED с ограничениями
- **Что:** `EntityLifecycleService`, `replace_slug`, resolver исторических URL
- **Файлы:** `services/entity_lifecycle.py`, `test_entity_lifecycle.py` (16)
- **Открыто:** G-1 (delete↔rename/create), G-2 (неизвестные колонки)

## S5 — Миграции (production)

- **Статус:** DEFERRED · **Блокирует:** production-schema gate

## S6 — SQLite reliability

- **Дата:** 2026-10-13 · **Статус:** ACCEPTED WITH LIMITATIONS
- **Что:** единая конфигурация фабрик, retry по BUSY, read/write scopes, `foreign_keys=ON`
- **Файлы:** `sqlite_provider.py`, `slug_registry.py`, `retry.py`,
  `services/entity_lifecycle.py`, `test_sqlite_reliability.py` (15)
- **Ограничения:** F-A1, F-B1/F-B2/F-B3

## S7 V1 — Backup + drill

- **Дата:** 2026-10-14 · **Статус:** ACCEPTED WITH LIMITATIONS
- **Что:** `create_backup`, `restore_backup`, storage-контракт, drill
- **Файлы:** `infrastructure/storage.py`, `backup.py`, `restore.py`, `test_backup_restore.py` (17)
- **Ограничения:** L-1…L-10 (изображения вне backup, FS-атомарность и др.)

## Product Slice V1

- **Дата:** 2026-10-14 · **Статус:** IMPLEMENTED WITH LIMITATIONS
- **Что:** каталог, админка, авторизация, изображения, публичный сайт
- **Тесты:** 167 → 172

## Universal Store Template V1

- **Дата:** 2026-10-15 · **Статус:** IMPLEMENTED WITH LIMITATIONS
- **Что:** настройки магазина (name, tagline, логотип, контакты, соцсети, SEO, валюта, языки),
  информационные страницы как данные
- **Тесты:** **184/184** (12 новых)
- **Ограничения:** U-1 (браузер тогда был недоступен), L-1…L-7

---

## Блок 3b-1 — многоязычные характеристики

- **Статус:** IMPLEMENTED · **Тесты:** → 288
- **Что:** `product_attributes.lang`, админ-селект языка в строке, `attributes_for(lang)`
  с цепочкой «язык → нейтральные → скрыть»
- **Файлы:** `migrations/catalog.py` (шаг 7), `domain/catalog.py`, `services/catalog.py`,
  `web/app.py`, `admin_product_form.html`, `tests/test_attributes_i18n.py`

## Таблица характеристик 3×12 (`3b-1-fix-TABLE`)

- **Статус:** IMPLEMENTED — UNCOMMITTED · **Тесты:** 288 → **291**
- **Что:** сетка `12 групп × (en, ru, ro)` (36 полей при `ATTRIBUTE_SLOTS = 48`),
  скрытый `attribute_lang_i` (язык = столбец), автоподстановка en→ru/ro,
  пустой en — строка не сохраняется, guard «>12 строк на язык» → 400,
  языковые нейтральные строки (`lang = ''`) формой не удаляются
- **Файлы:** `domain/catalog.py` (`fill_attribute_translations`), `services/catalog.py`
  (`DELETE … lang IN ('ru','ro','en')`), `web/app.py`, `admin_product_form.html`,
  `web/i18n.py`, `tests/test_attributes_i18n.py`

## Индикатор полноты перевода

- **Статус:** IMPLEMENTED — UNCOMMITTED · **Тесты:** 291 → **300**
- **Что:** колонка «Переводы» в `/admin/products` (EN/RU/RO, зелёный/красный),
  точка-предупреждение (нет описания/характеристик), постоянная легенда,
  фильтр `?incomplete=1` **только по именам**; `PROVEN`: фильтр и индикатор не считают
  fallback полнотой
- **Происхождение текста:** **не хранится** → «заполнено» ≠ «переведено» (**UNKNOWN**)

## Предупреждение при публикации (Phase 3)

- **Статус:** IMPLEMENTED — UNCOMMITTED · **Тесты:** 300 → **305**
- **Что:** `POST /admin/products/{id}/publish` публикует **всегда**; при отсутствии имени
  для en/ru/ro отдаёт `303` с `?missing=…` и баннер на странице товара; `400` **нет**;
  чекбокс `is_published` в форме публикации **не проверяет** (вне объёма)
- **Файлы:** `services/catalog.py` (`set_product_published` → `(Product, List[str])`),
  `web/app.py`, `admin_product_form.html`, `base.html`, `web/i18n.py`,
  `tests/test_publish_warning.py` (5)

## Layer 4 — консультант по комплекту

- **Статус:** IMPLEMENTED — UNCOMMITTED · **Тесты:** 305 → **316**
- **Что:** `GET /consultant` (404 в режиме `visitka`), 4 сценария (интервью, влог, свадьба,
  спорт), детерминированный движок без LLM/сети, `mount_map`, отказ по байонету,
  «уже есть» (6 чекбоксов), бюджет в MDL, CTA `mailto:` из `shop_settings`
- **Проверено на живых данных** (копия прод-БД): интервью **140 980 MDL** / 5 групп,
  свадьба **145 780** / 6 групп, влог **136 230** (+ гимбал опционально), спорт — отказ
- **Решения:** см. `PROJECT_STATE.md`, раздел «Решения Layer 4»

## Layer 4 — исправления

| Исправление | Причина | Тесты |
|---|---|---|
| `CATEGORY_ALIASES` (транслит-слаги → ключи правил) | на живом каталоге подбор возвращал «Нет подходящих», т.к. слаги `obektivy`/`svet` не совпадали с `lenses`/`lighting` | 316 → **319** |
| скрытое поле `lang` в GET-форме | после «Подобрать» язык сбрасывался в RU (форма теряла `?lang`) | 319 → **324** |
| визуальная проверка | выполнена Worker #2 по заданию владельца (headless-браузер, скриншоты); приёмка — за владельцем | — |

---

## Общая хронология

| # | Этап | Дата | Статус | Тесты |
|---|------|------|--------|-------|
| 1 | S1 | 2026-10-12 | IMPLEMENTED — NOT ACCEPTED | — |
| 2 | S2 | 2026-10-12 | ACCEPTED | — |
| 3 | S3 | 2026-10-12 | ACCEPTED | — |
| 4 | S4 | 2026-10-13 | ACCEPTED с ограничениями | — |
| 5 | S5 | — | DEFERRED | — |
| 6 | S6 | 2026-10-13 | ACCEPTED WITH LIMITATIONS | — |
| 7 | S7 V1 | 2026-10-14 | ACCEPTED WITH LIMITATIONS | — |
| 8 | Product Slice V1 | 2026-10-14 | IMPLEMENTED WITH LIMITATIONS | 167→172 |
| 9 | Universal Store Template V1 | 2026-10-15 | IMPLEMENTED WITH LIMITATIONS | 184 |
| 10 | 3b-1 характеристики + язык | — | IMPLEMENTED — UNCOMMITTED | 288 |
| 11 | Таблица 3×12 | — | IMPLEMENTED — UNCOMMITTED | 288→291 |
| 12 | Индикатор полноты | — | IMPLEMENTED — UNCOMMITTED | 291→300 |
| 13 | Публикация-предупреждение | — | IMPLEMENTED — UNCOMMITTED | 300→305 |
| 14 | **Layer 4 консультант** | — | IMPLEMENTED — UNCOMMITTED | 305→316 |
| 15 | Layer 4 фиксы | 2026-10-23 | IMPLEMENTED — UNCOMMITTED | 319→**324** |

> Даты этапов 10–15 в репозитории не зафиксированы (**UNKNOWN**): коммитов нет,
> есть только даты изменения файлов. Единственная точная дата — прогон 324 тестов
> 2026-10-23 21:28 и подготовка документации 2026-10-23.

---

## Открытые вопросы (сводно)

| # | Вопрос | Требует |
|---|--------|---------|
| **L-1** | Изображения вне backup S7 | Решение руководителя |
| **L-2** | `python-multipart` или JS-загрузка | Решение руководителя |
| **L-3** | Админ-формы на английском | Решение руководителя |
| **L-4** | Типизированные характеристики | Решение руководителя |
| **L-5** | Роли/аудит/смена пароля | Решение руководителя |
| **L-7** | Управление изображениями магазина | Решение руководителя |
| **S5** | Production schema | Открытие gate |
| **S8** | HTTP-контракт | Решение руководителя |
| **U-1** | Живой браузер | Выполнен для Layer 4 (по заданию владельца) |
| **U-3** | `VIDEOSHOP_DB_PATH` | Решение руководителя |
| **N-1** | Коммит VideoShop (весь showcase untracked) | Решение владельца |
| **N-2** | `.gitignore` исключает 4 файла памяти | Решение владельца |

---
Обновлено: 2026-10-23
