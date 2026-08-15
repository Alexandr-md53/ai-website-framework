from typing import Callable, Iterator, Optional
from .exceptions import SlugCollisionError


class DefaultCollisionResolver:
    """
    Канонический коллижен-резолвер для генерации уникальных слагов.
    """

    def iter_candidates(
        self,
        base_slug: str,
        max_length: Optional[int] = None,
        max_attempts: int = 100,
    ) -> Iterator[str]:
        """
        Чистый итератор кандидатов слагов: base, base-2, base-3 ...
        Применяет max_length к итоговому кандидату с учетом длины суффикса.
        """
        if max_length and len(base_slug) > max_length:
            yield base_slug[:max_length].rstrip("-")
        else:
            yield base_slug

        for attempt in range(1, max_attempts):
            suffix = f"-{attempt + 1}"
            if max_length:
                allowed_base_len = max_length - len(suffix)
                if allowed_base_len <= 0:
                    raise SlugCollisionError(
                        f"Cannot fit suffix '{suffix}' within max_length={max_length}"
                    )
                truncated_base = base_slug[:allowed_base_len].rstrip("-")
                yield f"{truncated_base}{suffix}"
            else:
                truncated_base = base_slug.rstrip("-")
                yield f"{truncated_base}{suffix}"

    def resolve(
        self,
        base_slug: str,
        is_available: Callable[[str], bool],
        max_length: Optional[int] = None,
        max_attempts: int = 100,
    ) -> str:
        """
        Синхронный API разрешения коллизий для SlugGenerator.generate_unique().
        """
        candidates = self.iter_candidates(
            base_slug=base_slug,
            max_length=max_length,
            max_attempts=max_attempts,
        )

        for candidate in candidates:
            if is_available(candidate):
                return candidate

        raise SlugCollisionError(
            f"Failed to generate unique slug for '{base_slug}' after {max_attempts} attempts."
        )
