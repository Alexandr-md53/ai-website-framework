import uuid
import pytest

from showcases.plant_nursery.domain.category import Category
from showcases.plant_nursery.validation.category_rules import CategoryHierarchyValidator

from ai_framework.validation import ValidationEngine, ValidationContext


class TestCategoryHierarchyValidation:
    @pytest.fixture
    def rules(self):
        return {"parent_id": [CategoryHierarchyValidator()]}

    @pytest.mark.asyncio
    async def test_valid_root_category(self, rules, category_repo):
        context = ValidationContext(persistence_provider=category_repo)
        engine = ValidationEngine(context=context)

        category = Category(
            id=uuid.uuid4(),
            name="Outdoor Plants",
            slug="outdoor-plants",
            parent_id=None,
        )
        payload = {"id": category.id, "parent_id": category.parent_id}

        result = await engine.validate(payload=payload, rules=rules)

        assert getattr(result, "is_valid", getattr(result, "valid", False)) is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_valid_child_category(self, rules, category_repo):
        context = ValidationContext(persistence_provider=category_repo)
        engine = ValidationEngine(context=context)

        parent = Category(
            id=uuid.uuid4(),
            name="Outdoor Plants",
            slug="outdoor-plants",
            parent_id=None,
        )
        category_repo.add(parent)

        child = Category(
            id=uuid.uuid4(), name="Shrubs", slug="shrubs", parent_id=parent.id
        )
        payload = {"id": child.id, "parent_id": child.parent_id}

        result = await engine.validate(payload=payload, rules=rules)

        assert getattr(result, "is_valid", getattr(result, "valid", False)) is True

    @pytest.mark.asyncio
    async def test_reject_nonexistent_parent_id(self, rules, category_repo):
        context = ValidationContext(persistence_provider=category_repo)
        engine = ValidationEngine(context=context)

        missing_parent_id = uuid.uuid4()
        category = Category(
            id=uuid.uuid4(), name="Shrubs", slug="shrubs", parent_id=missing_parent_id
        )
        payload = {"id": category.id, "parent_id": category.parent_id}

        result = await engine.validate(payload=payload, rules=rules)

        assert getattr(result, "is_valid", getattr(result, "valid", False)) is False
        assert any(
            e.field == "parent_id" and "not_found" in e.message_key
            for e in result.errors
        )

    @pytest.mark.asyncio
    async def test_reject_self_referencing_parent(self, rules, category_repo):
        context = ValidationContext(persistence_provider=category_repo)
        engine = ValidationEngine(context=context)

        cat_id = uuid.uuid4()
        category = Category(
            id=cat_id, name="Self Referencing", slug="self-ref", parent_id=cat_id
        )
        payload = {"id": category.id, "parent_id": category.parent_id}

        result = await engine.validate(payload=payload, rules=rules)

        assert getattr(result, "is_valid", getattr(result, "valid", False)) is False
        assert any(
            e.field == "parent_id" and "self_reference" in e.message_key
            for e in result.errors
        )

    @pytest.mark.asyncio
    async def test_reject_direct_cycle_a_b_a(self, rules, category_repo):
        context = ValidationContext(persistence_provider=category_repo)
        engine = ValidationEngine(context=context)

        cat_a = Category(
            id=uuid.uuid4(), name="Category A", slug="cat-a", parent_id=None
        )
        category_repo.add(cat_a)

        cat_b = Category(
            id=uuid.uuid4(), name="Category B", slug="cat-b", parent_id=cat_a.id
        )
        category_repo.add(cat_b)

        cat_a.parent_id = cat_b.id
        payload = {"id": cat_a.id, "parent_id": cat_a.parent_id}

        result = await engine.validate(payload=payload, rules=rules)

        assert getattr(result, "is_valid", getattr(result, "valid", False)) is False
        assert any(
            e.field == "parent_id" and "cyclic_dependency" in e.message_key
            for e in result.errors
        )

    @pytest.mark.asyncio
    async def test_reject_transitive_cycle_a_b_c_a(self, rules, category_repo):
        context = ValidationContext(persistence_provider=category_repo)
        engine = ValidationEngine(context=context)

        cat_a = Category(
            id=uuid.uuid4(), name="Category A", slug="cat-a", parent_id=None
        )
        cat_b = Category(
            id=uuid.uuid4(), name="Category B", slug="cat-b", parent_id=cat_a.id
        )
        cat_c = Category(
            id=uuid.uuid4(), name="Category C", slug="cat-c", parent_id=cat_b.id
        )

        category_repo.add(cat_a)
        category_repo.add(cat_b)
        category_repo.add(cat_c)

        cat_a.parent_id = cat_c.id
        payload = {"id": cat_a.id, "parent_id": cat_a.parent_id}

        result = await engine.validate(payload=payload, rules=rules)

        assert getattr(result, "is_valid", getattr(result, "valid", False)) is False
        assert any(
            e.field == "parent_id" and "cyclic_dependency" in e.message_key
            for e in result.errors
        )
