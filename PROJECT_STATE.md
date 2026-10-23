# PROJECT_STATE — VideoShop

> **Назначение:** долгосрочная память. Архитектура, стек, правила, решения.
> Обновляется редко (раз в несколько дней / после крупных этапов).

## Что за проект

**VideoShop** — универсальный шаблон интернет-магазина.
- Владелец магазина управляет каталогом через веб-панель
- Не требует редактирования кода / JSON / БД
- VideoShop — первый демонстрационный магазин

## Архитектура

### Слои

```
showcases/videoshop/
├── domain/          # модели (Product, Category, Page, Money), правила консультанта
│   ├── catalog.py   # Product.text(lang), attributes_for(lang), fill_attribute_translations
│   ├── scenarios.py # 4 сценария Layer 4 как данные + mount_map + CATEGORY_ALIASES
│   └── consultant.py# детерминированный движок подбора (без I/O)
├── infrastructure/  # SQLite-провайдер, миграции, backup, изображения
├── services/        # CRUD, настройки, страницы, корзина, заказы
├── security/        # PBKDF2 + cookie + CSRF (без пароля в коде)
├── web/             # FastAPI + Jinja-шаблоны + i18n RU/RO/EN
└── tests/           # 26 модулей, 324 теста
```

### Стек

| Компонент | Технология |
|-----------|-----------|
| HTTP | **FastAPI 0.141.1** |
| БД | **SQLite** (S1–S7 провайдер), схема **v8** |
| Шаблоны | **Jinja2 3.1.6** |
| Auth | **PBKDF2** + HMAC-cookie + CSRF |
| Изображения | **Pillow** (пресеты `catalog`/`detail`) |
| Деньги | **Integer minor units** |
| Языки | **RU/RO/EN** |

### Режимы магазина (`web/config.py`)

`visitka` (лендинг + заявка, **без каталога — 404**) · `catalog` (по умолчанию, без корзины) ·
`shop` (каталог + корзина). Режим задаётся **при старте** (`StoreConfig`), query-параметр
`?mode=` режим **не переключает**.

## Что реализовано

**S1–S7 (инфраструктура):** транзакции `BEGIN IMMEDIATE`, CAS + guards, slug registry,
entity lifecycle, reliability (retry BUSY, scopes), backup + restore drill.

**Продуктовые этапы:**

| Этап | Что | Тесты | Статус |
|---|---|---|---|
| Product Slice V1 | каталог, админка, изображения, авторизация | 167 → 172 | IMPLEMENTED WITH LIMITATIONS |
| Universal Store Template V1 | настройки магазина, страницы, SEO | → 184 | IMPLEMENTED WITH LIMITATIONS |
| 3b-1 (характеристики, языки) | `product_attributes.lang`, админ-селект языка | → 288 | IMPLEMENTED |
| Характеристики «таблица 3×12» | сетка 12×(en,ru,ro), автоподстановка, guard 12/язык | 288 → 291 | IMPLEMENTED |
| Полнота перевода | индикатор EN/RU/RO + фильтр `?incomplete=1` | 291 → 300 | IMPLEMENTED |
| Публикация неполного | предупреждение (не блок) + CTA | 300 → 305 | IMPLEMENTED |
| **Layer 4 — консультант** | `/consultant`, 4 сценария, детерминированные правила | → 316 | IMPLEMENTED |
| Layer 4 fixes | `CATEGORY_ALIASES`, `lang` в форме | 319 → **324** | IMPLEMENTED |

**Текущий базис: 324/324, 0 failed/errors/skipped** (прогон 2026-10-23 21:28, Worker #2).

## Решения Layer 4 (консультант)

| # | Решение | Где |
|---|---|---|
| L4-1 | Только детерминированные правила: данные каталога + утверждённые пороги, **без LLM/сети** | `domain/consultant.py` |
| L4-2 | 4 сценария: **интервью, влог, свадьба, спорт** | `domain/scenarios.py` |
| L4-3 | Байонет — **ручная таблица** `mount_map` (Canon→RF, Sony→FE), `mount_required`; товар без записи — **fail-closed** | `scenarios.py` |
| L4-4 | Категории каталога — транслит-слаги; правила — английские ключи; связь через `CATEGORY_ALIASES` | `scenarios.py` |
| L4-5 | «Уже есть» — чекбоксы 6 категорий; при «есть камера» объективы **не предлагаются** («укажите байонет») | `consultant.py` |
| L4-6 | Спорт: честный отказ по байонету, правило **не расширяется** | `scenarios.py` |
| L4-7 | CTA ведёт на `contact_email` из `shop_settings` (**не** `/request`) | `public_consultant.html` |
| L4-8 | Бюджет — только **MDL**, cap на **сумму остатка** после «уже есть» | `consultant.py` |
| L4-9 | Язык результата = язык формы: `lang` передаётся скрытым полем GET-формы | `public_consultant.html` |

Проверено на живых данных (копия прод-БД): интервью **140 980 MDL** (5 групп), свадьба
**145 780** (6 групп), влог **136 230** (+ опциональный гимбал), спорт — отказ.

## Ключевые решения (архитектурные, из ранних этапов)

- **D1** slug только в `slug_registry`; **D2** `update_record_cas`; **D3** `entity_id INTEGER`;
  **D5** hard delete + release slug в одной транзакции; **D6** resolver current/redirect/not_found;
  **D7** явный `entity_type`; **D9** released хранятся бессрочно; **D10** без tenant/language в slug.
- **S6:** `journal_mode=DELETE`, `synchronous=FULL`, WAL не включать; `busy_timeout=5000`;
  retry только по `SQLITE_BUSY`; `foreign_keys=ON`; разделение read/write scopes.
- **S7:** явный путь к БД; `backup()` — основной механизм; restore только с подтверждением
  и pre-restore snapshot.

## Из Nursery — взято / отклонено

**Взято:** конвейер изображений, UI-переводы (`get_ui`), валюта, сид только в пустую БД,
PRG-структура админки, транслитерация slug.

**Отклонено:** админка без авторизации, хардкод-секрет, характеристики-колонки,
check-then-insert уникальность, удаление категории без проверки, Flask+SQLAlchemy,
multipart, AI/Telegram/квизы.

## Глобальные правила

- **`ai_framework/` — FROZEN.** Café — отдельный продукт, не трогать.
  Nursery — только чтение.
- Изменения **только** в `showcases/videoshop/`.
- **Не коммитить** без разрешения. **Не удалять** неизвестные файлы.

## Backlog (по `CHECKPOINT.md` и открытым решениям)

`L-1` изображения в backup · `L-2` `python-multipart` · `L-3` локализация админ-форм ·
`L-4` типизированные характеристики · `L-5` роли/аудит · `L-7` управление изображениями ·
`U-3` `VIDEOSHOP_DB_PATH` · `S5` production-схема · `S8` HTTP-контракт · `S9` регрессия+CI ·
пагинация каталога · навигация на `/consultant` · CTA-кнопка.

## Следующий этап

**Layer 5 — не начат**, объём **UNKNOWN** (в репозитории плана нет).

## О числах тестов в документах

`669` (`START_HERE.md`, `AGENTS.md`) — baseline **framework**; `578` (`docs/README.md`) —
снимок документации Phase 16.5; `184` (`GATES_LOG.md`) — гейт VideoShop 2026-10-15.
Это **разные срезы разных подсистем**, а не противоречие и не текущее состояние.
Текущее состояние VideoShop — **324** (PROVEN).

---
Обновлено: 2026-10-23
