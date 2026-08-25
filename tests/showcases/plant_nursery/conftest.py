import pytest
from typing import Dict, Optional
import uuid

from showcases.plant_nursery.domain.category import Category


class InMemoryCategoryRepository:
    def __init__(self):
        self._storage: Dict[uuid.UUID, Category] = {}

    def add(self, category: Category) -> None:
        self._storage[category.id] = category

    def get(self, category_id: uuid.UUID) -> Optional[Category]:
        return self._storage.get(category_id)


@pytest.fixture
def category_repo():
    return InMemoryCategoryRepository()
