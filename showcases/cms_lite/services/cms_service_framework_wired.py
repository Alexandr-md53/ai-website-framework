from dataclasses import dataclass
from typing import Dict, List, Optional
import uuid
import re
import asyncio
import concurrent.futures

from showcases.cms_lite.domain.category import Category
from showcases.cms_lite.domain.tag import Tag
from showcases.cms_lite.domain.item import Item, SLUG_RE
from showcases.cms_lite.domain.item_status import (
    ItemStatus,
    InvalidStateTransitionError,
)
from showcases.cms_lite.domain.user import UserContext, UserRole, PermissionDeniedError
from showcases.cms_lite.infrastructure.persistence_adapter import (
    FrameworkInMemoryPersistenceProvider,
)

try:
    from ai_framework.validation.engine import ValidationEngine
    from ai_framework.validation.providers.metadata import InMemoryMetadataProvider
    from ai_framework.validation.providers.persistence import (
        InMemoryPersistenceProvider as ValidationPersistenceProvider,
    )
    from ai_framework.validation.context import ValidationContext
    from ai_framework.crud.slug_orchestrator import AsyncSlugOrchestrator
    from ai_framework.crud.engine import UniversalCRUDEngine
    from ai_framework.services.slug import SlugGenerator, DefaultCollisionResolver

    FRAMEWORK_AVAILABLE = True
    FRAMEWORK_IMPORT_ERROR = ""
except Exception as e:
    FRAMEWORK_AVAILABLE = False
    FRAMEWORK_IMPORT_ERROR = str(e)


class NotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass


class CmsLiteFrameworkWiredService:
    def _run_async(self, coro):
        try:
            loop = asyncio.get_running_loop()
            is_running = loop.is_running()
        except RuntimeError:
            is_running = False
        if is_running:
            with concurrent.futures.ThreadPoolExecutor() as ex:
                return ex.submit(asyncio.run, coro).result()
        else:
            return asyncio.run(coro)

    def __init__(self):
        self._categories: Dict[uuid.UUID, Category] = {}
        self._tags: Dict[uuid.UUID, Tag] = {}
        self._items: Dict[uuid.UUID, Item] = {}
        self._category_slugs: Dict[str, uuid.UUID] = {}
        self._tag_slugs: Dict[str, uuid.UUID] = {}
        self._item_slugs: Dict[str, uuid.UUID] = {}

        if not FRAMEWORK_AVAILABLE:
            raise RuntimeError(
                f"Framework contracts not available: {FRAMEWORK_IMPORT_ERROR}"
            )

        self.crud_persistence = FrameworkInMemoryPersistenceProvider()

        self.metadata_provider = InMemoryMetadataProvider(
            schemas={
                "Category": {"name": ["required"], "slug": ["required", "slug"]},
                "Tag": {"name": ["required"], "slug": ["required", "slug"]},
                "Item": {
                    "title": ["required"],
                    "slug": ["required", "slug"],
                    "content": ["required"],
                    "category_id": ["required"],
                },
            }
        )

        self.validation_persistence = ValidationPersistenceProvider()

        self.validation_context = ValidationContext(
            metadata_provider=self.metadata_provider,
            persistence_provider=self.validation_persistence,
        )
        self.validation_engine = ValidationEngine(context=self.validation_context)

        self.slug_generator = SlugGenerator()
        self.collision_resolver = DefaultCollisionResolver()
        self.slug_orchestrator = AsyncSlugOrchestrator(
            slug_generator=self.slug_generator,
            collision_resolver=self.collision_resolver,
            persistence_provider=self.crud_persistence,
            default_source_field="title",
            default_target_field="slug",
        )

        self.crud_engine = UniversalCRUDEngine(
            persistence_provider=self.crud_persistence,
            validation_engine=self.validation_engine,
            slug_orchestrator=self.slug_orchestrator,
        )

    def _require_role(self, user: Optional[UserContext], allowed: List[UserRole]):
        if user is None:
            raise PermissionDeniedError("Unauthorized: no user context")
        if user.role not in allowed:
            raise PermissionDeniedError(f"Forbidden: role {user.role} not in {allowed}")

    def _is_slug_unique(
        self,
        slug: str,
        index: Dict[str, uuid.UUID],
        exclude_id: Optional[uuid.UUID] = None,
    ) -> bool:
        if slug not in index:
            return True
        if exclude_id and index[slug] == exclude_id:
            return True
        return False

    def _run_validation(self, entity_name: str, payload: dict):
        async def _validate():
            result = await self.validation_engine.validate_entity(entity_name, payload)
            return result

        result = self._run_async(_validate())
        if not result.valid:
            errors = result.errors if hasattr(result, "errors") else []
            msg = str(errors[0]) if errors else f"validation.failed:{entity_name}"
            raise ValidationError(msg)

    def _run_slug_orchestration(self, entity_name: str, payload: dict) -> dict:
        async def _process():
            processed = await self.slug_orchestrator.process(
                entity_name=entity_name, payload=payload
            )
            return processed

        return self._run_async(_process())

    def create_category(
        self, user: UserContext, name: str, slug: str, description: Optional[str] = None
    ) -> Category:
        self._require_role(user, [UserRole.ADMIN, UserRole.EDITOR])
        slug = slug.strip().lower()
        if not SLUG_RE.match(slug):
            raise ValidationError(f"validation.invalid_slug_format:slug={slug}")
        if not self._is_slug_unique(slug, self._category_slugs):
            raise ValidationError(f"validation.not_unique:slug={slug}")
        payload = {"name": name, "slug": slug, "description": description}
        self._run_validation("Category", payload)

        async def _insert():
            res = await self.crud_engine.create("Category", payload)
            if not res.success:
                raise ValidationError(str(res.errors))
            return res.data

        self._run_async(_insert())
        cat = Category(id=uuid.uuid4(), name=name, slug=slug, description=description)
        cat.validate()
        self._categories[cat.id] = cat
        self._category_slugs[slug] = cat.id
        return cat

    def list_categories(self) -> List[Category]:
        return list(self._categories.values())

    def create_tag(self, user: UserContext, name: str, slug: str) -> Tag:
        self._require_role(user, [UserRole.ADMIN, UserRole.EDITOR])
        slug = slug.strip().lower()
        if not SLUG_RE.match(slug):
            raise ValidationError(f"validation.invalid_slug_format:slug={slug}")
        if not self._is_slug_unique(slug, self._tag_slugs):
            raise ValidationError(f"validation.not_unique:slug={slug}")
        payload = {"name": name, "slug": slug}
        self._run_validation("Tag", payload)

        async def _insert():
            res = await self.crud_engine.create("Tag", payload)
            if not res.success:
                raise ValidationError(str(res.errors))
            return res.data

        self._run_async(_insert())
        tag = Tag(id=uuid.uuid4(), name=name, slug=slug)
        tag.validate()
        self._tags[tag.id] = tag
        self._tag_slugs[slug] = tag.id
        return tag

    def list_tags(self) -> List[Tag]:
        return list(self._tags.values())

    def create_item(
        self,
        user: UserContext,
        title: str,
        slug: str,
        content: str,
        category_id: uuid.UUID,
        tag_ids: Optional[List[uuid.UUID]] = None,
    ) -> Item:
        self._require_role(user, [UserRole.ADMIN, UserRole.EDITOR])
        slug = slug.strip().lower()
        if not SLUG_RE.match(slug):
            raise ValidationError(f"validation.invalid_slug_format:slug={slug}")
        if not self._is_slug_unique(slug, self._item_slugs):
            raise ValidationError(f"validation.not_unique:slug={slug}")
        if category_id not in self._categories:
            raise NotFoundError(f"Category {category_id} not found")
        if tag_ids:
            for tid in tag_ids:
                if tid not in self._tags:
                    raise NotFoundError(f"Tag {tid} not found")
        payload = {
            "title": title,
            "slug": slug,
            "content": content,
            "category_id": str(category_id),
        }
        self._run_validation("Item", payload)
        processed_payload = self._run_slug_orchestration("Item", payload)
        final_slug = processed_payload.get("slug", slug)

        async def _insert():
            res = await self.crud_engine.create("Item", processed_payload)
            if not res.success:
                raise ValidationError(str(res.errors))
            return res.data

        self._run_async(_insert())

        def _is_uuid(s: str) -> bool:
            try:
                uuid.UUID(s)
                return True
            except:
                return False

        item = Item(
            id=uuid.uuid4(),
            title=title,
            slug=final_slug,
            content=content,
            category_id=category_id,
            tag_ids=tag_ids or [],
            author_id=uuid.UUID(user.user_id) if _is_uuid(user.user_id) else None,
        )
        try:
            item.validate_for_draft()
        except ValueError as e:
            raise ValidationError(str(e))
        self._items[item.id] = item
        self._item_slugs[final_slug] = item.id
        return item

    def _get_item(self, item_id: uuid.UUID) -> Item:
        if item_id not in self._items:
            raise NotFoundError(f"Item {item_id} not found")
        return self._items[item_id]

    def update_item_content(
        self,
        user: UserContext,
        item_id: uuid.UUID,
        title: Optional[str] = None,
        content: Optional[str] = None,
        slug: Optional[str] = None,
    ) -> Item:
        self._require_role(user, [UserRole.ADMIN, UserRole.EDITOR])
        item = self._get_item(item_id)
        if slug and slug != item.slug:
            slug = slug.strip().lower()
            if not SLUG_RE.match(slug):
                raise ValidationError(f"validation.invalid_slug_format:slug={slug}")
            if not self._is_slug_unique(slug, self._item_slugs, exclude_id=item.id):
                raise ValidationError(f"validation.not_unique:slug={slug}")
            del self._item_slugs[item.slug]
            self._item_slugs[slug] = item.id
            item.slug = slug
        if title is not None:
            item.title = title
        if content is not None:
            item.content = content
        try:
            item.validate_for_draft()
        except ValueError as e:
            raise ValidationError(str(e))
        return item

    def publish_item(self, user: UserContext, item_id: uuid.UUID) -> Item:
        self._require_role(user, [UserRole.ADMIN, UserRole.EDITOR])
        item = self._get_item(item_id)
        try:
            item.publish()
        except Exception as e:
            raise ValidationError(str(e))
        return item

    def unpublish_item(self, user: UserContext, item_id: uuid.UUID) -> Item:
        self._require_role(user, [UserRole.ADMIN, UserRole.EDITOR])
        item = self._get_item(item_id)
        item.unpublish()
        return item

    def duplicate_item(self, user: UserContext, item_id: uuid.UUID) -> Item:
        self._require_role(user, [UserRole.ADMIN, UserRole.EDITOR])
        src = self._get_item(item_id)
        new_slug_base = f"{src.slug}-copy"
        candidate = new_slug_base
        counter = 1
        while not self._is_slug_unique(candidate, self._item_slugs):
            counter += 1
            candidate = f"{new_slug_base}-{counter}"
        dup = Item(
            id=uuid.uuid4(),
            title=f"{src.title} (copy)",
            slug=candidate,
            content=src.content,
            category_id=src.category_id,
            status=ItemStatus.DRAFT,
            tag_ids=list(src.tag_ids),
            media_ids=list(src.media_ids),
            seo_title=src.seo_title,
            seo_description=src.seo_description,
            og_title=src.og_title,
            og_description=src.og_description,
        )
        self._items[dup.id] = dup
        self._item_slugs[dup.slug] = dup.id
        return dup

    def get_published_by_slug(self, slug: str) -> Item:
        slug = slug.strip().lower()
        item_id = self._item_slugs.get(slug)
        if not item_id:
            raise NotFoundError(f"Item slug {slug} not found")
        item = self._items[item_id]
        if not item.is_published():
            raise NotFoundError(f"Item {slug} not published - public cannot read")
        return item

    def list_published(
        self,
        category_id: Optional[uuid.UUID] = None,
        tag_id: Optional[uuid.UUID] = None,
    ) -> List[Item]:
        result = [i for i in self._items.values() if i.is_published()]
        if category_id:
            result = [i for i in result if i.category_id == category_id]
        if tag_id:
            result = [i for i in result if tag_id in i.tag_ids]
        return result

    def search_published(self, query: str) -> List[Item]:
        q = query.lower()
        return [
            i
            for i in self.list_published()
            if q in i.title.lower() or q in i.content.lower() or q in i.slug.lower()
        ]

    def list_all_items(
        self, user: UserContext, status: Optional[ItemStatus] = None
    ) -> List[Item]:
        self._require_role(user, [UserRole.ADMIN, UserRole.EDITOR])
        items = list(self._items.values())
        if status:
            items = [i for i in items if i.status == status]
        return items

    def search_items(
        self, user: UserContext, query: str, only_published=False
    ) -> List[Item]:
        self._require_role(user, [UserRole.ADMIN, UserRole.EDITOR])
        q = query.lower()
        items = self._items.values()
        if only_published:
            items = [i for i in items if i.is_published()]
        return [i for i in items if q in i.title.lower() or q in i.content.lower()]

    def get_item_admin(self, user: UserContext, item_id: uuid.UUID) -> Item:
        self._require_role(user, [UserRole.ADMIN, UserRole.EDITOR])
        return self._get_item(item_id)


CmsLiteService = CmsLiteFrameworkWiredService
