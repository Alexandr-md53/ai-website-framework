import uuid
from typing import Any, Dict, Optional

from ai_framework.validation import Validator, ValidationContext


class CategoryHierarchyValidator(Validator):
    """Кастомный валидатор Phase 6 для проверки иерархии категорий."""

    async def validate(
        self,
        field: str,
        value: Any,
        payload: Dict[str, Any],
        context: Optional[ValidationContext] = None,
    ) -> Optional[Dict[str, Any]]:
        parent_id = value
        if parent_id is None:
            return None

        cat_id = payload.get("id")

        # 1. Проверка self-reference
        if cat_id is not None and parent_id == cat_id:
            return {
                "field": field,
                "message_key": "validation.self_reference",
                "params": {},
            }

        # Извлечение репозитория из persistence_provider
        repo = context.persistence_provider if context else None
        if not repo:
            return None

        # 2. Проверка существования родителя
        parent = repo.get(parent_id)
        if not parent:
            return {
                "field": field,
                "message_key": "validation.not_found",
                "params": {},
            }

        # 3. Проверка циклических зависимостей (A -> B -> A, A -> B -> C -> A)
        visited = {cat_id} if cat_id else set()
        current_parent_id: Optional[uuid.UUID] = parent_id

        while current_parent_id is not None:
            if current_parent_id in visited:
                return {
                    "field": field,
                    "message_key": "validation.cyclic_dependency",
                    "params": {},
                }

            visited.add(current_parent_id)
            parent_node = repo.get(current_parent_id)

            if not parent_node:
                break

            current_parent_id = getattr(parent_node, "parent_id", None)

        return None
