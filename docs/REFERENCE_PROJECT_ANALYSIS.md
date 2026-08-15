# Reference Project Analysis: Plant Nursery → AI Website Framework

**Document Version:** 4.0 (Canonical Sync)  
**Last Reviewed:** 2026-08-14  
**Status:** Active Baseline  

---

## 1. Key Takeaway (Главный вывод)

Phase 5 использует Reference Implementation («Питомник») для выявления требований и существующих подходов, но каждый Framework-модуль проектируется и реализуется заново под canonical architecture `ai_framework`, с последующей generalization и TDD-проверкой. **Код Reference Project не считается Framework implementation.**

Проект «Питомник» является **Reference Implementation** — эталонным клиентским приложением, используемым для валидации универсальности архитектуры `ai_framework`.

---

## 2. What is a Reference Implementation?

The Plant Nursery project is not the Framework itself.
It is the first complete application built on top of the Framework architecture.

Its purpose is to validate architectural decisions, test Core components, and demonstrate application layering.

---

## 3. Архитектурная декомпозиция компонентов (Framework Breakdown)

| Компонент | Роль в Питомнике | Архитектурный слой | Назначение во Фреймворке | Фактический статус |
| :--- | :--- | :--- | :--- | :--- |
| **Validation Engine** | Проверка схем и данных | **`[CORE]`** | Движок валидации правил (`ai_framework.validation`) | ✅ **COMPLETE** (Included in 241-test Block A baseline) |
| **CRUD Engine** | Управление сущностями | **`[CORE]`** | Универсальный CRUD-слой (`ai_framework.crud`) | ✅ **COMPLETE** (Included in 241-test Block A baseline) |
| **AI Provider Subsystem**| API Нейросетей | **`[CORE]`** | Модульные провайдеры (`ai_framework.ai_provider`) | ✅ **COMPLETE** (Included in 241-test Block A baseline) |
| **AI Pipeline Engine** | Конвейер генерации AI | **`[CORE]`** | Оркестрация и парсинг (`ai_framework.pipeline`) | ✅ **COMPLETE** (Included in 241-test Block A baseline) |
| **Slug Service (`SLG_01`)**| Формирование URL | **`[CORE SERVICES - TARGET]`**| Сервис генерации человекочитаемых ссылок | ⏳ **NOT IMPLEMENTED** (Phase 5 Target) |
| **Asset Manager (`ASM_01`)**| Загрузка файлов/медиа | **`[CORE SERVICES - TARGET]`**| Менеджер медиаассетов | ⏳ **NOT IMPLEMENTED** (Phase 5 Target) |
| **Localization Engine (`LOC_01`)**| Перевод интерфейса | **`[CORE - TARGET]`** | Универсальный движок мультиязычности | ⏳ **NOT IMPLEMENTED** (Phase 5 Target) |
| **Persistence Layer (`DB_01`)**| Абстракция БД/ORM | **`[CORE / DB - TARGET]`** | Слой абстракции данных | ⏳ **NOT IMPLEMENTED** (Phase 5 Target) |
| **Metadata Engine (`MD_01`)**| Спецификации полей | **`[CORE - TARGET]`** | Движок метаданных сущностей | 📋 **PLANNED** (Phase 6 Target) |
| **Admin Platform (`ADM_01`)**| Интерфейс админки | **`[PLANNED ADMIN]`**| Платформа администрирования на Metadata | 📋 **PLANNED** (Phase 6 Target) |
| **Application Shell** | `app.py` / `main.py` | **`[PROJECT]`** | Точка входа конкретного приложения | 🟢 **PROJECT DOMAIN** |
| **Plant Entity** | Модель саженцев | **`[PROJECT]`** | Отраслевая бизнес-сущность | 🟢 **PROJECT DOMAIN** |

---

## 4. Матрица Миграции (Framework Migration Matrix)

Каноничная структура Core-пакета: `ai_framework/`

| Было в Питомнике | Станет / Является во Фреймворке | Канонический путь | Слой |
| :--- | :--- | :--- | :--- |
| `framework/validation/` | Validation Engine | `ai_framework.validation` | **`[CORE - COMPLETE]`** |
| `framework/crud/` | Universal CRUD Engine | `ai_framework.crud` | **`[CORE - COMPLETE]`** |
| `openrouter_api.py` | AI Provider Subsystem | `ai_framework.ai_provider` | **`[CORE - COMPLETE]`** |
| `framework/pipeline.py` | AI Pipeline & Orchestration | `ai_framework.pipeline` | **`[CORE - COMPLETE]`** |
| `services/slug_service.py` | Slug Service (`SLG_01`) | `ai_framework.services.slug` | **`[CORE SERVICES - TARGET]`** |
| `services/image_service.py`| Asset Manager (`ASM_01`) | `ai_framework.services.asset` | **`[CORE SERVICES - TARGET]`** |
| `translations/ui.py` | Localization Engine (`LOC_01`)| `ai_framework.localization` | **`[CORE - TARGET]`** |
| `models.py` / DB helpers | Persistence Layer (`DB_01`) | `ai_framework.db` | **`[CORE / DB - TARGET]`** |

---

## 5. Текущий статус компонентов (Current Migration Status)

| Статус | Описание |
| :--- | :--- |
| ✅ **Implemented (Block A)** | Реализовано в `ai_framework/`, зафиксировано в релизе `1.0.0-stable`, Block A tests passed |
| ⏳ **Phase 5 Target** | Разрабатывается с нуля под канонический `ai_framework/` с генерализацией и TDD |
| 📋 **Phase 6+ Planned** | Запланировано на следующие этапы (Metadata Engine, Admin Platform) |

---

## 6. Золотые архитектурные правила платформы (Core Principles)

1. **Zero Domain Knowledge in Core:** Ядро (`ai_framework`) не содержит слов `Plant`, `Watering`, `Nursery` или специфики других бизнесов.
2. **Canonical Imports Only:** Все импорты выполняются строго через `ai_framework.<module>`. Пакет `framework/` полностью удален и запрещен.
3. **No Code Copying:** Клиентские проекты подключают Фреймворк как пакет (`pip install -e .`). Код референсного проекта не считается кодом фреймворка.
4. **Single Source of Truth:** Документация отражает только реально существующий в репозитории код.

---

## 7. Block A Assessment Summary

* **Canonical Package:** `ai_framework`  
* **Test Suite Status:** **241 / 241 PASSED (0 failures, 0 warnings)**  
* **Release Version:** `1.0.0-stable`