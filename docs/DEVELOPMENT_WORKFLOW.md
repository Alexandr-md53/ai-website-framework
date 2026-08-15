# Development Workflow & Architecture Standard

## 1. Core vs Application Boundary

### AI Website Framework Core
**Location:** `ai_framework/`

**Contains:**
- Universal engines (e.g., `ValidationEngine`)
- Core contracts and interfaces
- Base validators
- Data providers
- Framework services
- Reusable infrastructure abstractions

**The Core MUST NOT contain:**
- Domain concepts (`Plant`, `Category`, `Nursery`, `Cafe`, `Dentist`, etc.)
- Client-specific schemas
- Client-specific business rules

---

### Application / Reference Project
**Location:** Client repository or reference application modules.

**Contains:**
- Domain models
- Domain schemas (e.g., `PlantSchema`)
- Business rules & policy definitions
- Multilingual mapping
- Application handlers
- ORM persistence
- Application-specific integrations

> **Rule:** `PlantSchema` belongs to the Plant Nursery application, NOT to `ai_framework`.

---

## 2. Single Source of Truth & Import Integrity

### Single Source of Truth Rule
Every Core module MUST have exactly one canonical implementation.
* `ai_framework.validation` is the only authoritative implementation of the Validation Engine.
* Parallel implementations, forks, or copies of Core modules must not exist in Reference Projects, client projects, legacy `framework/` packages, or temporary directories.
* If a legacy copy exists, it must be removed or explicitly marked as deprecated.

### Import Integrity Rule
Before completing a module migration:
1. Search the repository for old package names (e.g., `framework.validation`).
2. Verify that no Core module imports the legacy package.
3. Verify that tests import the canonical package (`ai_framework`).
4. Verify that the application does not contain a duplicate Core implementation.
5. Run the complete test suite.

---

## 3. Package Architecture & Installation

### Package Installation Rule
`AI_Website_Framework` MUST be installable as a standard Python package.

Client projects MUST consume the Framework through:
```bash

# Reference Project Analysis: Plant Nursery -> AI Website Framework (v3.1)

## 1. Key Takeaway (Главный вывод)
Анализ показал, что проект «Питомник» уже содержит большинство компонентов, необходимых для фреймворка. Задача следующего этапа — не переписать проект с нуля, а выделить из него универсальные сервисы (Core Services), отделить отраслевую логику (Domain) и оставить в Project только данные и особенности конкретного клиента. Таким образом, «Питомник» становится не конечным продуктом, а Reference Implementation — эталонным проектом, на котором проверяется архитектура Framework.

---

## 2. What is a Reference Implementation?

The Plant Nursery project is not the Framework itself.
It is the first complete implementation built on top of the Framework architecture.

Its purpose is to validate architectural decisions, test new Core components, and demonstrate how a real business project should be structured.

**Future reference projects may include:**
* Cafe / Bakery
* Restaurant / Delivery
* Lawyer / Legal Agency
* Dentist / Medical Clinic
* Portfolio / Resume

---

## 3. Архитектурная декомпозиция компонентов (Framework Breakdown)

| Компонент | Роль в Питомнике | Архитектурный слой | Назначение во Фреймворке |
| :--- | :--- | :--- | :--- |
| **Metadata Engine** | Спецификации полей и связей | **`[CORE]`** | Single source of truth for entities, forms, generators, validation rules, localization, and publishing pipelines. |
| **Generator Pipeline**| Конвейер обработки AI | **`[CORE]`** | Execution Engine for Content Workflows & Pipelines |
| **CRUD Engine** | Управление растениями/категориями | **`[CORE]`** | Универсальный движок CRUD для любых Entity / Content Types |
| **Category Engine** | Древовидные структуры и категории | **`[CORE]`** | Универсальный модуль иерархии и категоризации |
| **Localization Engine**| Перевод интерфейса (`ui.py`) | **`[CORE]`** | Универсальный движок мультиязычности (JSON/gettext) |
| **Template Engine** | Рендеринг HTML/Jinja2 | **`[CORE]`** | Универсальный движок рендеринга шаблонов |
| **Plugin Registry** | Реестр модулей | **`[CORE]`** | Система регистрации и вызова плагинов |
| **Persistence Layer**| Подключение к DB/ORM | **`[CORE]`** | Слой абстракции данных (SQLite, PostgreSQL, Supabase) |
| **Settings Manager** | Конфигурация `.env` | **`[CORE]`** | Единый менеджер настроек и ключей API |
| **Slug Service** | Формирование URL-адресов | **`[CORE SERVICES]`**| Сервис генерации понятных человекочитаемых ссылок |
| **Asset Manager** | Загрузка фото растений | **`[CORE SERVICES]`**| Менеджер медиа (изображения, PDF, AI-ассеты, файлы) |
| **OpenRouter / OpenAI**| API Нейросетей | **`[AI PROVIDERS]`** | Модульные провайдеры для подключения LLM-моделей |
| **Telegram / Website**| Публикация постов | **`[PLUGINS]`** | Внешние плагины публикации в каналы и сайты |
| **Admin Platform** | Базовый интерфейс админки | **`[ADMIN PLATFORM]`**| Самостоятельная платформа администрирования, строящая UI исключительно на Metadata |
| **Content Engine** | Блог, статьи, новости | **`[DOMAIN]`** | Универсальный контентный модуль (Blog, FAQ, News) |
| **Business Theme** | Стили и элементы макета | **`[DOMAIN]`** | Шаблон темы оформления (Каталог, Визитка, Лендинг) |
| **Plant Entity** | Поля и свойства саженцев | **`[PROJECT]`** | Отраслевая бизнес-сущность Питомника |
| **Plant Categories** | Категории ("Хвойные", "Цветущие") | **`[PROJECT]`** | Конкретные категории выбранного бизнеса |
| **Plant Design** | Иконки полива, стили саженцев | **`[PROJECT]`** | Визуальное оформление конкретно под питомник |

---

## 4. Матрица Миграции (Framework Migration Matrix)

| Было в Питомнике (`site_generation_post`) | Станет во Фреймворке (`AI Website Framework`) | Слой |
| :--- | :--- | :--- |
| `app.py` / `main.py` | `Core Application` | **`[CORE]`** |
| `models.py` (`Plant`) | `Project Entity` (`Plant` в `project/models.py`) | **`[PROJECT]`** |
| `routes/admin_categories.py` | `Category Engine` / `CRUD Engine` | **`[CORE]`** |
| `publishers/telegram_publisher.py` | `Telegram Plugin` (`plugins/telegram/`) | **`[PLUGINS]`** |
| `publishers/registry.py` | `Plugin Registry` (`core/registry.py`) | **`[CORE]`** |
| `framework/pipeline.py` | `Generator Pipeline` (`generators/pipeline.py`)| **`[CORE]`** |
| `framework/metadata.py` | `Metadata Engine` (`metadata/`) | **`[CORE]`** |
| `services/image_service.py` | `Asset Manager` (`services/asset_manager.py`) | **`[CORE SERVICES]`** |
| `services/slug_service.py` | `Slug Service` (`services/slug.py`) | **`[CORE SERVICES]`** |
| `translations/ui.py` | `Localization Engine` (`core/localization.py`) | **`[CORE]`** |
| `openrouter_api.py` | `AI Provider Layer` (`ai/providers/`) | **`[AI PROVIDERS]`** |
| `templates/admin/` | `Admin Platform` (`admin/`) | **`[ADMIN PLATFORM]`** |

---

## 5. Текущий статус миграции (Current Migration Status)

| Модуль / Компонент | Архитектурный слой | Статус миграции |
| :--- | :--- | :--- |
| **Plugin Registry** | `[CORE]` | ✅ Завершено (Covered by tests) |
| **AI Layer / Providers** | `[AI PROVIDERS]` | ✅ Завершено (Covered by tests) |
| **Metadata Engine** | `[CORE]` | ✅ Завершено (Covered by tests) |
| **Generator Pipeline** | `[CORE]` | ✅ Завершено (Covered by tests) |
| **Template Engine** | `[CORE]` | ✅ Завершено (Covered by tests) |
| **Localization Engine** | `[CORE]` | ✅ Завершено (Covered by tests) |
| **Slug Service** | `[CORE]` | ✅ Завершено (Covered by tests) |
| **Asset Manager** | `[CORE]` | ✅ Завершено (Covered by tests) |
| **Persistence Layer** | `[CORE / DB]` | ✅ Завершено (Covered by tests) |
| **Validation Engine** | `[CORE]` ✅ Завершено (Covered by tests) |
| **Configuration Manager** | `[CORE]` | ⏳ В очереди |
| **CRUD Engine** | `[CORE]` | ⏳ В очереди |
| **Admin Platform** | `[ADMIN PLATFORM]` | ⏳ В очереди |
| **Dynamic Forms Engine** | `[ADMIN PLATFORM]` | ⏳ В очереди |

---

## 6. Золотые архитектурные правила платформы (Core Principles)

1. **Zero Domain Knowledge in Core**: Ядро (`CORE`) не содержит слов `Plant`, `Watering`, `Nursery` или названий любых других бизнесов.
2. **Metadata-Driven UI**: Админка, таблицы, генераторы и формы строятся исключительно на основе `Metadata Engine`.
3. **Pluggable Architecture**: Все внешние сервисы (Telegram, VK, CMS) подключаются строго через `Plugin Registry`.
4. **Everything is Metadata First**: Никаких форм, никаких CRUD-операций, никаких таблиц без декларации в Metadata.
5. **Framework before Project**: Нельзя добавлять новую функциональность в `PROJECT`, пока не определено, не должна ли она жить в `CORE` или `CORE SERVICES`.
6. **Reference Project Validates Framework**: Reference Project подтверждает правильность и универсальность Framework, но Framework никогда не адаптруется и не идит на костыли ради одного Reference Project.

---

## 7. Next Migration Steps (Последовательность переноса)
Localization Engine (Core)
│
▼

Slug Service (Core Services)
│
▼

Asset Manager (Core Services)
│
▼

Universal CRUD Engine (Core)
│
▼

Admin Platform (Admin Shell & Dynamic Forms)
│
▼

Full Plant Nursery Reference Migration
---

## 8. Strategic Vision Note
> *«AI Website Framework is the Core of the future AI Website Platform.»*

## Validation Engine v1.0 — Quality Assessment

Status: ✅ Production Ready

Test Summary:

- 121 tests passed
- Public API fully covered
- Built-in validators fully tested
- Integration tests completed
- Edge cases covered
- Dependency Injection verified

Coverage Notes:

Overall coverage is intentionally lower than the business logic coverage because several modules contain only:

- Protocol definitions
- TypedDict / TypeAlias declarations
- Abstract provider interfaces
- Debug helper methods (__repr__)
- Defensive branches

These modules do not contain executable business logic and are therefore not artificially covered to increase the overall coverage percentage.

Design Principle:

Coverage is evaluated primarily on executable business logic rather than on structural type definitions or interface declarations.