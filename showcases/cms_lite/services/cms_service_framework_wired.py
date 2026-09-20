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
    from showcases.cms_lite.domain.media import Media
except Exception:
    # fallback minimal Media if domain/media.py not yet exists
    from dataclasses import dataclass as _dataclass

    @_dataclass
    class Media:
        id: uuid.UUID
        filename: str
        filepath: str
        media_type: str = "image"
        item_id: Optional[uuid.UUID] = None
        alt_text: Optional[str] = None

        def to_dict(self):
            return {
                "id": str(self.id),
                "filename": self.filename,
                "filepath": self.filepath,
                "media_type": self.media_type,
                "item_id": str(self.item_id) if self.item_id else None,
                "alt_text": self.alt_text,
            }


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
        self._media: Dict[uuid.UUID, Media] = {}
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
        # Normalize role: allow str "editor" -> UserRole.EDITOR
        role = user.role
        if isinstance(role, str):
            try:
                role = UserRole(role.upper())
            except Exception:
                pass
            # update context for downstream checks (optional)
            try:
                user.role = role
            except Exception:
                pass
        if role not in allowed:
            # try also compare by value for str vs enum
            role_vals = [r.value if hasattr(r, "value") else str(r) for r in allowed]
            role_str = role.value if hasattr(role, "value") else str(role)
            if (
                role_str.upper() not in [v.upper() for v in role_vals]
                and role not in allowed
            ):
                raise PermissionDeniedError(
                    f"Forbidden: role {user.role} not in {allowed}"
                )

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
        # category_id may come as str -> normalize to UUID
        if isinstance(category_id, str):
            try:
                category_id = uuid.UUID(category_id)
            except Exception:
                # allow lookup by slug
                if category_id in self._category_slugs:
                    category_id = self._category_slugs[category_id]
                else:
                    raise NotFoundError(f"Category {category_id} not found")
        if category_id not in self._categories:
            raise NotFoundError(f"Category {category_id} not found")
        if tag_ids:
            norm_tags = []
            for tid in tag_ids:
                if isinstance(tid, str):
                    try:
                        tid = uuid.UUID(tid)
                    except Exception:
                        continue
                if tid not in self._tags:
                    raise NotFoundError(f"Tag {tid} not found")
                norm_tags.append(tid)
            tag_ids = norm_tags
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
        # allow str
        if isinstance(item_id, str):
            try:
                item_id = uuid.UUID(item_id)
            except Exception:
                # try lookup by slug
                if item_id in self._item_slugs:
                    item_id = self._item_slugs[item_id]
                else:
                    raise NotFoundError(f"Item {item_id} not found")
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
            canonical_url=getattr(src, "canonical_url", None),
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
            if isinstance(category_id, str):
                try:
                    category_id = uuid.UUID(category_id)
                except Exception:
                    pass
            result = [i for i in result if i.category_id == category_id]
        if tag_id:
            result = [i for i in result if tag_id in i.tag_ids]
        return result

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

    def get_item(self, item_id: uuid.UUID) -> Item:
        # public alias for _get_item
        return self._get_item(item_id)

    # ==================== Phase 5 SEO + Media ====================

    def _validate_seo(
        self, seo_title, seo_description, og_title, og_description, canonical_url
    ):
        if seo_title is not None and len(seo_title) > 70:
            raise ValidationError(f"seo_title length {len(seo_title)} exceeds max 70")
        if seo_description is not None and len(seo_description) > 160:
            raise ValidationError(
                f"seo_description length {len(seo_description)} exceeds max 160"
            )
        if og_title is not None and len(og_title) > 70:
            raise ValidationError(f"og_title length {len(og_title)} exceeds max 70")
        if og_description is not None and len(og_description) > 200:
            raise ValidationError(
                f"og_description length {len(og_description)} exceeds max 200"
            )
        if canonical_url is not None and canonical_url != "":
            if not (
                canonical_url.startswith("http://")
                or canonical_url.startswith("https://")
                or canonical_url.startswith("/")
            ):
                raise ValidationError(
                    f"canonical_url must start with http://, https:// or / — got {canonical_url!r}"
                )

    def update_item_seo(
        self,
        user: UserContext,
        item_id: uuid.UUID,
        seo_title: Optional[str] = None,
        seo_description: Optional[str] = None,
        og_title: Optional[str] = None,
        og_description: Optional[str] = None,
        canonical_url: Optional[str] = None,
    ) -> Item:
        self._require_role(user, [UserRole.ADMIN, UserRole.EDITOR])
        item = self._get_item(item_id)
        self._validate_seo(
            seo_title, seo_description, og_title, og_description, canonical_url
        )

        # Use domain method if exists, otherwise set directly
        if hasattr(item, "update_seo"):
            # Item.update_seo expects None = keep, "" = clear
            item.update_seo(
                seo_title=seo_title,
                seo_description=seo_description,
                og_title=og_title,
                og_description=og_description,
                canonical_url=canonical_url,
            )
        else:
            if seo_title is not None:
                item.seo_title = seo_title or None
            if seo_description is not None:
                item.seo_description = seo_description or None
            if og_title is not None:
                item.og_title = og_title or None
            if og_description is not None:
                item.og_description = og_description or None
            if canonical_url is not None:
                item.canonical_url = None if canonical_url == "" else canonical_url
        return item

    def create_media(
        self,
        user: UserContext,
        filename: str,
        filepath: str,
        media_type: str = "image",
        alt_text: Optional[str] = None,
    ) -> Media:
        self._require_role(user, [UserRole.ADMIN, UserRole.EDITOR])
        if not filename:
            raise ValidationError("filename required")
        media_id = uuid.uuid4()
        media = Media(
            id=media_id,
            filename=filename,
            filepath=filepath,
            media_type=media_type,
            alt_text=alt_text,
        )
        self._media[media_id] = media
        return media

    def attach_media_to_item(
        self, user: UserContext, item_id: uuid.UUID, media_id: uuid.UUID
    ) -> Item:
        self._require_role(user, [UserRole.ADMIN, UserRole.EDITOR])
        item = self._get_item(item_id)
        # media_id may be str
        if isinstance(media_id, str):
            try:
                media_id = uuid.UUID(media_id)
            except Exception:
                raise NotFoundError(f"Media {media_id} not found")
        if media_id not in self._media:
            raise NotFoundError(f"Media {media_id} not found")
        if media_id not in item.media_ids:
            item.media_ids.append(media_id)
        # bind
        try:
            self._media[media_id].item_id = item.id
        except Exception:
            pass
        return item

    def detach_media_from_item(
        self, user: UserContext, item_id: uuid.UUID, media_id: uuid.UUID
    ) -> Item:
        self._require_role(user, [UserRole.ADMIN, UserRole.EDITOR])
        item = self._get_item(item_id)
        if isinstance(media_id, str):
            try:
                media_id = uuid.UUID(media_id)
            except Exception:
                # idempotent: if can't parse, just ensure not in list (by str compare)
                item.media_ids = [
                    mid for mid in item.media_ids if str(mid) != str(media_id)
                ]
                return item
        if media_id in item.media_ids:
            item.media_ids = [mid for mid in item.media_ids if mid != media_id]
        if media_id in self._media:
            try:
                if getattr(self._media[media_id], "item_id", None) == item.id:
                    self._media[media_id].item_id = None
            except Exception:
                pass
        return item

    def list_item_media(self, item_id: uuid.UUID) -> List[Media]:
        item = self._get_item(item_id)
        result = []
        for mid in item.media_ids:
            m = self._media.get(mid)
            if m:
                result.append(m)
        return result


CmsLiteService = CmsLiteFrameworkWiredService
