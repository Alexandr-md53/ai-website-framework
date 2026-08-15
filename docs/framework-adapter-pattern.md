Architecture Specification: Validation Integration & Adapter Layer
1. Overview & Core PhilosophyAI_Website_Framework придерживается принципа строгого разделения ответственности (Separation of Concerns).
Ядро валидации (ValidationEngine) проектируется как чистое, изолированное окружение, свободное от зависимостей от конкретных веб-фреймворков (Flask, Django, FastHTTP), ORM-слоев (SQLAlchemy) или специфичных моделей данных конкретных проектов.
Валидация в экосистеме Framework строится на 5-слойной архитектуре, где ключевым мостом между инфраструктурой приложения и ядром выступает Adapter Layer.
2. The 5-Layer Integration ModelPlaintext┌─────────────────────────────────────────────────────────┐
│                    Application Layer                    │
│                  (Flask / HTTP / Forms)                 │
└────────────────────────────┬────────────────────────────┘
                             │ Raw Payload (HTTP Strings, Forms)
                             ▼
┌─────────────────────────────────────────────────────────┐
│                    Adapter / Schema                     │
│    • Input Normalization (defaults, empty str -> None)  │
│    • Engine Payload Framing                             │
│    • Compatibility API (e.g. tuple (data, errors))      │
└────────────────────────────┬────────────────────────────┘
                             │ Normalized Data
                             ▼
┌─────────────────────────────────────────────────────────┐
│                    Validation Engine                    │
│    • Execution of Pure Rules & Rulesets                 │
│    • Immutable ValidationResult Contract                │
└────────────────────────────┬────────────────────────────┘
                             │ Validated Data
                             ▼
┌─────────────────────────────────────────────────────────┐
│                   Business Layer / Service              │
│    • Domain Logic & Multilingual Mapping                │
│    • Type Coercion for DB (e.g., decimal -> int cents)  │
└────────────────────────────┬────────────────────────────┘
                             │ Domain Entities / DTOs
                             ▼
┌─────────────────────────────────────────────────────────┐
│                       Persistence                       │
│                   (SQLAlchemy / DB Engine)              │
└────────────────────────────┬────────────────────────────┘
Responsibility Matrix
СлойОтветственностьЧего слой НЕ должен делать
-ApplicationПрием HTTP-запросов, сессии, маршрутизация.Не должен содержать бизнес-правила и логику преобразования типов.
-Adapter / SchemaНормализация сырых HTTP-данных, подстановка defaults, вызов ValidationEngine, адаптация ответа под контроллер.Не должен выполнять персистенцию (БД) или сложный бизнес-маппинг.
-Validation EngineВыполнение атомарных и составных правил валидации, формирование ValidationResult.Не должен знать о HTTP-контексте, Flask request или моделях SQLAlchemy.-Business / ServiceПрименение доменных правил, обработка локализации (multilingual mapping), финальное приведение типов для БД.Не должен дублировать базовую проверку типов/форматов.
-PersistenceЗапись и чтение данных из хранилища.Не должен содержать валидацию пользовательского ввода.

3. Core Architectural Principles
3.1. Normalization vs. Validation
- Rule: Validation Engine validates the normalized input contract. Input normalization belongs to the Integration / Adapter layer.
-Сырые данные из HTTP-форм часто приходят в виде строк ("100.50", "", "true").
-Adapter отвечает за первичную нормализацию: пустые строки преобразуются в None, отсутствующим необязательным полям присваиваются значение по умолчанию (field.default).-ValidationEngine принимает нормализованный словарь и проверяет соответствие контракту типов и бизнес-ограничений.- Implicit Type Coercion (автоматическое неконтролируемое приведение типов) внутри ядра ValidationEngine запрещено без явной конфигурации в спецификации схемы.
3.2. Native ValidationResult & Compatibility API
- Rule: Application-specific schemas may expose a simplified validation contract without changing the native ValidationResult contract of the Validation Engine. -ValidationEngine.validate() всегда возвращает строго объект ValidationResult.
-Если приложение или legacy-контроллер ожидает упрощенный контракт (например, кортеж (data, errors)), эта адаптация реализуется исключительно внутри адаптера схемы (например, PlantSchema.validate()).
-Изменение контракта ValidationEngine ради удобства отдельных веб-контроллеров не допускается.
3.3. Separation of Domain Transformations
- Rule: Validation Engine validates input structure; Service Layer decides how validated data is transformed and mapped to domain models.
-Преобразования, специфичные для конкретного хранилища или бизнес-модели (например, перевод цены из float/string в системные копейки int, или раскладывание полей по языковым колонкам name_ru / name_en), относятся к Service Layer и не переносятся в ядро фреймворка.
4. Implementation Guidelines for Adapters
При создании нового адаптера сущности в приложении (Reference Project или клиентском сервисе) необходимо следовать шаблону:Pythonclass BaseSchemaAdapter:

    """Стандартный базовый паттерн адаптера для AI_Website_Framework."""
    
    def __init__(self, engine: ValidationEngine):
        self._engine = engine

    def _normalize_input(self, raw_data: dict) -> dict:
        """Нормализация: очистка пустых строк, дефолты."""
        normalized = {}
        # Логика нормализации адаптера
        return normalized

    def validate(self, raw_data: dict) -> tuple[dict, dict]:
        """Compatibility API for Web Handlers."""
        prepared_data = self._normalize_input(raw_data)
        
        # Native Engine call
        result: ValidationResult = self._engine.validate(prepared_data)
        
        if result.is_valid:
            return result.clean_data, {}
        return {}, result.errors