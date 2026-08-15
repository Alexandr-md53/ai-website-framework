# Reference Project Migration: Plant Entity Schema Contract

## 📌 Context
- **Entity:** Plant (Питомник)
- **Engine Version:** Validation Engine v1.0
- **Stage:** 3.1 — PlantSchema Contract
- **Date:** August 2026

---

## 🚨 Migration Decisions

### 1. Price Type Conflict Resolution
- **Frontend:** `<input type="number" step="0.01" required>` (expects Float/Decimal, mandatory)
- **Database:** `db.Column(db.Integer, nullable=True)` (expects Integer, optional at DB layer)
- **Decision:**
  1. Set `required=True` in `PlantSchema` to match HTML form enforcement.
  2. Normalize to `Number` (Float/Int) at Validation Engine layer.
  3. Keep `int()` conversion on the Service Layer before DB persist to avoid breaking DB schema.

### 2. Category Existence Check
- **Decision:** `category_id` type/required validation is handled **Synchronously** by `PlantSchema`. Checking whether the Category ID actually exists in the database is classified as **Delegated / External State Validation** and performed at the Service Layer.

---

## 📋 Verified Field Contract Table

| Input Name | Normalized Type | Required? | Min/Max Length | Numeric Range | Allowed Values | Source | Validation Rule | Validation Type |
| :--- | :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| `category_id` | `Integer` | **Yes** | — | — | — | HTML + DB Model | `fields.Integer()` + `GreaterThan(0)` | Sync Field |
| `name` | `String` | **Yes** | 1 / 150 | — | — | HTML + DB Model | `fields.String()` + `Length(1, 150)` | Sync Field |
| `price` | `Number` | **Yes** | — | — | — | HTML (`step=0.01`) | `fields.Number()` | Sync Field |
| `promotion_percent` | `Integer` | **No** | — | 0 .. 100 | — | HTML (`min=0 max=100`) | `fields.Integer()` + `Range(0, 100)` | Sync Field |
| `promotion_message` | `String` | **No** | — | — | — | DB Model | `fields.String()` | Sync Field |
| `description` | `String` | **No** | — | — | — | DB Model | `fields.String()` | Sync Field |
| `light` | `String` | **No** | 0 / 150 | — | — | DB Model | `fields.String()` + `Length(max=150)` | Sync Field |
| `evergreen` | `String` | **No** | 0 / 150 | — | — | DB Model | `fields.String()` + `Length(max=150)` | Sync Field |
| `maintenance` | `String` | **No** | 0 / 150 | — | — | DB Model | `fields.String()` + `Length(max=150)` | Sync Field |
| `height` | `String` | **No** | 0 / 150 | — | — | DB Model | `fields.String()` + `Length(max=150)` | Sync Field |
| `lang` | `String` | **No** | — | — | `'ru'`, `'en'`, `'ro'` | App Route Rule | `fields.String()` + `Choice(...)` | Sync Field |

*Note: `slug` (server-generated) and `image` (file upload) are excluded from `PlantSchema` as Infrastructure/Service concerns.*

# Plant Migration Contract & Verification Results

## 1. Status Overview
- **Status:** COMPLETED ✅
- **Engine:** `ai_framework.validation`
- **Target Component:** `PlantSchema`
- **Regression Result:** 7/7 passed (`pytest -q`)

---

## 2. Standardized Schema Contract
`PlantSchema` использует адаптер над `ValidationEngine`, предоставляя совместимый интерфейс для контроллеров и сервисов.

* **Validation Method:** `PlantSchema.validate(raw_data)`
* **Return Format:** `(data: dict, errors: dict)`
* **HTTP/Form Integration:** Принимает строковые значения из HTTP/HTML-форм, выполняет первичную нормализацию (дефолты, пустые строки -> `None`).

---

## 3. Approved Migration Decisions

### Price Handling (HTML vs DB)
* **Decision:** `ValidationEngine` проверяет валидность числового формата из HTTP-запроса (допускает decimal/string). 
* **Conversion:** Приведение к `int` для записи в БД производится на уровне Handler/Service layer, а не внутри ядра валидации.

### Optional & Multilingual Fields
* **Normalization:** Необязательные поля приводятся к корректным типам на этапе адаптера.
* **Localization (`lang=ru/en/ro`):** Логика локализации и маппинга языковых полей сохраняется в сервисном слое. Валидатор проверяет только корректность структуры данных.

### Legacy Warnings
* **SQLAlchemy `Query.get()` Warning:** Игнорируется в рамках миграции валидации, так как относится к обновлению ORM API и не затрагивает контракт `ValidationEngine`.

---

## 4. Quality Gate Checklist
- [x] Business Rules Inventory
- [x] Rule Verification
- [x] PlantSchema Implementation
- [x] Handler Migration
- [x] Migration Tests (7/7 passed)
- [x] Full Regression Suite (`pytest -q`)