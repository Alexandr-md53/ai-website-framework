import inspect
from typing import Any, Optional


class CRUDEngine:
    """
    Высокоуровневый schema-aware фасад CRUD.

    Отвечает за:
    - чтение __slug_config__ из Pydantic-схем/моделей;
    - интеграцию со SlugGenerator;
    - проверку уникальности slug через persistence.exists(field, value, exclude_id);
    - сохранение через persistence.save(data).

    Возвращает domain-level dict, а не CRUDResult.
    """

    def __init__(
        self,
        persistence: Any = None,
        slug_service: Any = None,
    ):
        self.persistence = persistence
        self.slug_service = slug_service

    def _get_slug_config(self, schema: Any) -> Optional[Any]:
        return getattr(schema, "__slug_config__", None)

    async def _await_if_needed(self, value: Any) -> Any:
        if inspect.isawaitable(value):
            return await value
        return value

    async def _check_exists(
        self,
        field: str,
        value: Any,
        exclude_id: Any = None,
    ) -> bool:
        if self.persistence is None:
            return False

        exists_fn = getattr(self.persistence, "exists", None)
        if exists_fn is not None:
            result = exists_fn(
                field,
                value,
                exclude_id=exclude_id,
            )
            return bool(await self._await_if_needed(result))

        is_unique_fn = getattr(self.persistence, "is_unique", None)
        if is_unique_fn is not None:
            try:
                result = is_unique_fn(field, value)
            except TypeError:
                result = is_unique_fn("entity", field, value)
            is_unique = await self._await_if_needed(result)
            return not bool(is_unique)

        return False

    async def _get_existing_record(
        self,
        schema: Any,
        entity_id: Any,
    ) -> dict:
        if self.persistence is None or entity_id is None:
            return {}

        entity_name = getattr(schema, "__name__", "entity").lower()

        # 1. Вызов методов извлечения на persistence provider
        method_names = ["fetch", "get", "find", "get_by_id", "fetch_by_id", "read"]
        for method_name in method_names:
            fn = getattr(self.persistence, method_name, None)
            if fn is not None and callable(fn):
                for args in [(entity_name, entity_id), (entity_id,)]:
                    try:
                        res = fn(*args)
                        res = await self._await_if_needed(res)
                        if isinstance(res, dict) and res:
                            return res
                    except (TypeError, ValueError, KeyError, AttributeError):
                        continue

        # 2. Извлечение из атрибутов хранилища провайдера (при отсутствии явных методов)
        storage_attrs = ["storage", "data", "records", "_storage", "_data", "_records", "db", "_db"]
        for attr in storage_attrs:
            container = getattr(self.persistence, attr, None)
            if isinstance(container, dict):
                if entity_id in container and isinstance(container[entity_id], dict):
                    return container[entity_id]
                if entity_name in container and isinstance(container[entity_name], dict):
                    if entity_id in container[entity_name]:
                        return container[entity_name][entity_id]
            elif isinstance(container, (list, tuple)):
                for item in container:
                    if isinstance(item, dict) and item.get("id") == entity_id:
                        return item

        return {}

    async def _resolve_slug_for_create(
        self,
        schema: Any,
        payload: dict,
    ) -> dict:
        updated_payload = dict(payload)
        slug_config = self._get_slug_config(schema)

        if not slug_config:
            return updated_payload

        if self.slug_service is None:
            raise RuntimeError(
                "slug_service is required when schema has __slug_config__"
            )

        target_field = getattr(slug_config, "target_field", "slug")
        source_field = getattr(slug_config, "source_field", "title")
        auto_generate = getattr(slug_config, "auto_generate", True)

        if target_field in updated_payload and updated_payload[target_field]:
            custom_slug = updated_payload[target_field]
            if await self._check_exists(target_field, custom_slug):
                raise ValueError(f"Custom slug '{custom_slug}' already exists")
            return updated_payload

        if (
            auto_generate
            and source_field in updated_payload
            and updated_payload[source_field]
        ):
            source_text = updated_payload[source_field]
            base_slug = self.slug_service.generate(source_text)

            candidate = base_slug
            counter = 1

            while await self._check_exists(target_field, candidate):
                counter += 1
                candidate = f"{base_slug}-{counter}"

            updated_payload[target_field] = candidate

        return updated_payload

    async def _resolve_slug_for_update(
        self,
        schema: Any,
        entity_id: Any,
        payload: dict,
        existing_record: dict,
    ) -> dict:
        updated_payload = dict(payload)
        slug_config = self._get_slug_config(schema)

        if not slug_config:
            return updated_payload

        if self.slug_service is None:
            raise RuntimeError(
                "slug_service is required when schema has __slug_config__"
            )

        target_field = getattr(slug_config, "target_field", "slug")
        source_field = getattr(slug_config, "source_field", "title")
        overwrite_on_update = getattr(
            slug_config,
            "overwrite_on_update",
            False,
        )

        # 1. Передан явный custom slug
        if target_field in updated_payload and updated_payload[target_field]:
            custom_slug = updated_payload[target_field]
            if await self._check_exists(
                target_field,
                custom_slug,
                exclude_id=entity_id,
            ):
                raise ValueError(f"Custom slug '{custom_slug}' already exists")
            return updated_payload

        # 2. Сохраняем существующий slug, если overwrite_on_update=False
        if not overwrite_on_update and target_field in existing_record:
            updated_payload[target_field] = existing_record[target_field]
            return updated_payload

        # 3. Перегенерация слага
        if (
            overwrite_on_update
            and source_field in updated_payload
            and updated_payload[source_field]
        ):
            source_text = updated_payload[source_field]
            base_slug = self.slug_service.generate(source_text)

            candidate = base_slug
            counter = 1

            while await self._check_exists(
                target_field,
                candidate,
                exclude_id=entity_id,
            ):
                counter += 1
                candidate = f"{base_slug}-{counter}"

            updated_payload[target_field] = candidate

        return updated_payload

    async def create(
        self,
        schema: Any,
        payload: dict,
    ) -> dict:
        processed_payload = await self._resolve_slug_for_create(schema, payload)

        if self.persistence is not None:
            save_fn = getattr(self.persistence, "save", None)
            if save_fn is not None:
                result = save_fn(processed_payload)
                return await self._await_if_needed(result)

        return processed_payload

    async def update(
        self,
        schema: Any,
        entity_id: Any,
        payload: dict,
    ) -> dict:
        existing_record = await self._get_existing_record(schema, entity_id)

        processed_payload = await self._resolve_slug_for_update(
            schema,
            entity_id,
            payload,
            existing_record,
        )

        processed_payload.setdefault("id", entity_id)

        save_fn = getattr(self.persistence, "save", None)
        if save_fn is not None:
            result = save_fn(processed_payload)
            return await self._await_if_needed(result)

        return processed_payload