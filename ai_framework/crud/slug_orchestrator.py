import inspect
from typing import Any, Optional
from ai_framework.crud.contracts import CRUDContext

try:
    from ai_framework.services.slug import SlugGenerator, DefaultCollisionResolver
except ImportError:
    try:
        from ai_framework.services.slug.generator import (
            SlugGenerator,
            DefaultCollisionResolver,
        )
    except ImportError:
        try:
            from ai_framework.slug.generator import (
                SlugGenerator,
                DefaultCollisionResolver,
            )
        except ImportError:
            SlugGenerator = None
            DefaultCollisionResolver = None


class AsyncSlugOrchestrator:
    """
    Асинхронный оркестратор слагов.
    Связывает бизнес-логику генерации (SlugGenerator + DefaultCollisionResolver)
    с асинхронным слоем сохранения (persistence_provider) для асинхронного разрешения коллизий.
    """

    def __init__(
        self,
        slug_generator: Any = None,
        collision_resolver: Any = None,
        persistence_provider: Any = None,
        default_source_field: str = "title",
        default_target_field: str = "slug",
    ):
        if slug_generator is not None:
            self.slug_generator = slug_generator
        elif SlugGenerator is not None:
            self.slug_generator = SlugGenerator()
        else:
            self.slug_generator = None

        if collision_resolver is not None:
            self.collision_resolver = collision_resolver
        elif DefaultCollisionResolver is not None:
            self.collision_resolver = DefaultCollisionResolver()
        else:
            self.collision_resolver = None

        self.persistence_provider = persistence_provider
        self.default_source_field = default_source_field
        self.default_target_field = default_target_field

    async def _await_if_needed(self, val: Any) -> Any:
        if inspect.isawaitable(val):
            return await val
        return val

    def _generate_base_slug(self, source_text: str) -> str:
        if self.slug_generator:
            gen_fn = getattr(self.slug_generator, "generate", None) or getattr(
                self.slug_generator, "slugify", None
            )
            if gen_fn:
                return gen_fn(source_text)

        # Fallback при отсутствии slug_generator
        return source_text.lower().strip().replace(" ", "-")

    async def _resolve_collision_async(
        self,
        entity_name: str,
        target_field: str,
        base_slug: str,
    ) -> str:
        if not self.persistence_provider:
            return base_slug

        is_unique_fn = getattr(
            self.persistence_provider,
            "is_unique",
            getattr(self.persistence_provider, "check_unique", None),
        )

        if not is_unique_fn:
            return base_slug

        max_attempts = (
            getattr(self.collision_resolver, "max_attempts", 100)
            if self.collision_resolver
            else 100
        )

        for attempt in range(1, max_attempts + 1):
            if attempt == 1:
                candidate = base_slug
            elif self.collision_resolver and hasattr(
                self.collision_resolver, "format_candidate"
            ):
                candidate = self.collision_resolver.format_candidate(base_slug, attempt)
            else:
                candidate = f"{base_slug}-{attempt}"

            res = is_unique_fn(entity_name, target_field, candidate)
            is_unique = await self._await_if_needed(res)

            if is_unique:
                return candidate

        raise RuntimeError(
            f"Could not resolve unique slug for '{base_slug}' after {max_attempts} attempts."
        )

    async def process(
        self,
        entity_name: str,
        payload: dict,
        context: Optional[CRUDContext] = None,
        source_field: Optional[str] = None,
        target_field: Optional[str] = None,
    ) -> dict:
        """
        Основная точка входа для UniversalCRUDEngine.
        Обогащает payload сгенерированным уникальным слагом.
        """
        updated_payload = dict(payload)

        src_field = source_field or self.default_source_field
        tgt_field = target_field or self.default_target_field

        # Если слаг уже передан в payload и он не пустой — не перезаписываем его
        if tgt_field in updated_payload and updated_payload[tgt_field]:
            return updated_payload

        source_val = updated_payload.get(src_field)
        if not source_val or not isinstance(source_val, str):
            return updated_payload

        base_slug = self._generate_base_slug(source_val)
        unique_slug = await self._resolve_collision_async(
            entity_name=entity_name,
            target_field=tgt_field,
            base_slug=base_slug,
        )

        updated_payload[tgt_field] = unique_slug
        return updated_payload
