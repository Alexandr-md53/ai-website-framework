# VideoShop — showcase

Демонстрационный интернет-магазин на `ai_framework` (первый продуктовый шоукейс).
Владелец наполняет каталог через веб-панель, без правки кода, JSON или БД.

**Возможности:** каталог и карточки товаров; админка (категории, товары, характеристики,
фото, страницы, настройки) с PBKDF2-авторизацией и CSRF; три языка интерфейса
**RU/RO/EN**; характеристики товара сеткой **12 групп × (en, ru, ro)** с автоподстановкой;
индикатор полноты перевода и фильтр неполных; предупреждение при публикации неполного
товара; **консультант по комплекту** (4 сценария, детерминированные правила).

## Требования

- **Python ≥ 3.10** (`pyproject.toml`: `requires-python = ">=3.10"`); проверено на 3.14.3.
- Зависимости в `pyproject.toml` **не объявлены** (`dependencies = []`) — они ставятся
  в окружение. Проверенные версии: `fastapi 0.141.1`, `starlette 1.6.0`, `uvicorn 0.52.1`,
  `jinja2 3.1.6`, `pillow 12.3.0`, `httpx 0.28.1` (для `TestClient`), `pytest 9.1.1`.

```powershell
pip install fastapi uvicorn jinja2 pillow httpx pytest
```

## Запуск

Из **корня репозитория** (чтобы работал импорт `showcases.*`). Каталоги данных должны
существовать заранее — хранилище требует абсолютный путь и готовый каталог:

```powershell
New-Item -ItemType Directory -Force data/db, data/backups | Out-Null

$env:VIDEOSHOP_SECRET_KEY = "<случайная строка>"
$env:VIDEOSHOP_ADMIN_USER = "owner"
$env:VIDEOSHOP_ADMIN_PASSWORD = "<пароль>"        # либо VIDEOSHOP_ADMIN_PASSWORD_HASH

python -c "import os, uvicorn; from showcases.videoshop.web.app import create_app; d = os.path.abspath('data'); app = create_app(db_path=os.path.join(d, 'db', 'shop.sqlite'), backup_dir=os.path.join(d, 'backups'), images_dir=os.path.join(d, 'images')); uvicorn.run(app, host='127.0.0.1', port=8000)"
```

> `launch_shop.py` в корне репозитория делает то же самое с жёстко заданными абсолютными
> путями (`data/db`, `data/backups`, `data/images`), но **намеренно не в Git**
> (см. `.gitignore`); команда выше самодостаточна.

Сайт: `http://127.0.0.1:8000/` · админка: `http://127.0.0.1:8000/admin` · консультант:
`http://127.0.0.1:8000/consultant` (доступен в режимах `catalog` и `shop`, в `visitka` — 404).

## Переменные окружения

| Переменная | Назначение |
|---|---|
| `VIDEOSHOP_SECRET_KEY` | подпись cookie сессии и CSRF; **без неё админка не работает (fail-closed)** |
| `VIDEOSHOP_ADMIN_USER` | имя администратора |
| `VIDEOSHOP_ADMIN_PASSWORD` | пароль администратора (хешируется при старте) |
| `VIDEOSHOP_ADMIN_PASSWORD_HASH` | готовый PBKDF2-хеш вместо пароля |
| `VIDEOSHOP_SESSION_TTL_SECONDS` | время жизни сессии |

Паролей и ключей по умолчанию в коде **нет** (`security/admin.py`).

**Режимы магазина:** `visitka` / `catalog` (по умолчанию) / `shop` задаются объектом
`StoreConfig` при создании приложения (`create_app(store_config=StoreConfig(mode="shop"))`).
Переменная `VIDEOSHOP_STORE_MODE` объявлена в `web/config.py`, но к `create_app`
**не подключена** — без явного `store_config` режим всегда `catalog`.

## Тесты

324 теста (0 skipped, 0 errors).

```powershell
# из папки showcase (используется её pyproject.toml: pythonpath = "../..")
cd showcases/videoshop
python -m pytest

# либо из корня репозитория с явным путём
python -m pytest showcases/videoshop/tests
```

Из корня **без пути** `python -m pytest` шоукейс не подхватит: в корневом `pytest.ini`
`testpaths = tests`.

## Локальные данные (вне Git)

| Путь | Назначение |
|---|---|
| `data/db/shop.sqlite` | рабочая БД SQLite (схема v8, миграции применяются при старте) |
| `data/db/shop.backup-YYYYMMDD-HHMMSS.sqlite` | бэкапы БД (пример: `shop.backup-20261022-215338.sqlite`) |
| `data/backups/` | каталог бэкапов приложения |
| `data/images/` | загруженные через админку фотографии товаров и категорий |

Эти каталоги **не коммитятся**: в них данные владельца. Упакованные изображения витрины
(герой, логотип, категории, портфолио, плейсхолдер) лежат в `web/static/media/` и **в Git входят** —
они отдаются маршрутами `/media/{file}` и `/media/portfolio/{file}` (`web/app.py`).

## Не коммитить (генерируемое)

`__pycache__/`, `*.pyc`, `.pytest_cache/`, `showcases/videoshop/reports/snapshots/`
(генерируемые HTML-снимки страниц).

## Границы

- `ai_framework/` — **FROZEN**, не изменять.
- **Café** — отдельный продукт, не трогать.
- **Nursery** (`site_generation_post/`) — только чтение.
- Изменения — **только** в `showcases/videoshop/`.
- **Не коммитить** без разрешения владельца.

## Документы проекта

В корне репозитория:

- [`CONTEXT.md`](../../CONTEXT.md) — шпаргалка для старта
- [`CHECKPOINT.md`](../../CHECKPOINT.md) — текущее состояние и долги
- [`PROJECT_STATE.md`](../../PROJECT_STATE.md) — архитектура и решения
- [`GATES_LOG.md`](../../GATES_LOG.md) — краткая история этапов
