from typing import Dict, List, Optional, Tuple
import uuid
import re
from showcases.cms_lite.domain.category import Category
from showcases.cms_lite.domain.tag import Tag
from showcases.cms_lite.domain.item import Item, SLUG_RE
from showcases.cms_lite.domain.media import Media
from showcases.cms_lite.domain.item_status import ItemStatus, InvalidStateTransitionError
from showcases.cms_lite.domain.user import UserContext, UserRole, PermissionDeniedError

class NotFoundError(Exception):
    pass

class ValidationError(Exception):
    pass

class CmsLiteService:
    def __init__(self):
        self._categories: Dict[uuid.UUID, Category] = {}
        self._tags: Dict[uuid.UUID, Tag] = {}
        self._items: Dict[uuid.UUID, Item] = {}
        self._media: Dict[uuid.UUID, Media] = {}
        # slug uniqueness indexes
        self._category_slugs: Dict[str, uuid.UUID] = {}
        self._tag_slugs: Dict[str, uuid.UUID] = {}
        self._item_slugs: Dict[str, uuid.UUID] = {}

    # ---- Auth guard ----
    def _require_role(self, user: Optional[UserContext], allowed: List[UserRole]):
        if user is None:
            raise PermissionDeniedError("Unauthorized: no user context")
        if user.role not in allowed:
            raise PermissionDeniedError(f"Forbidden: role {user.role} not in {allowed}")

    def _is_slug_unique(self, slug: str, index: Dict[str, uuid.UUID], exclude_id: Optional[uuid.UUID]=None) -> bool:
        if slug not in index:
            return True
        if exclude_id and index[slug] == exclude_id:
            return True
        return False

    # ---- Category CRUD ----
    def create_category(self, user: UserContext, name: str, slug: str, description: Optional[str]=None) -> Category:
        self._require_role(user, [UserRole.ADMIN, UserRole.EDITOR])
        slug = slug.strip().lower()
        if not SLUG_RE.match(slug):
            raise ValidationError(f"validation.invalid_slug_format:slug={slug}")
        if not self._is_slug_unique(slug, self._category_slugs):
            raise ValidationError(f"validation.not_unique:slug={slug}")
        cat = Category(id=uuid.uuid4(), name=name, slug=slug, description=description)
        cat.validate()
        self._categories[cat.id]=cat
        self._category_slugs[slug]=cat.id
        return cat

    def list_categories(self) -> List[Category]:
        return list(self._categories.values())

    # ---- Tag CRUD ----
    def create_tag(self, user: UserContext, name: str, slug: str) -> Tag:
        self._require_role(user, [UserRole.ADMIN, UserRole.EDITOR])
        slug = slug.strip().lower()
        if not SLUG_RE.match(slug):
            raise ValidationError(f"validation.invalid_slug_format:slug={slug}")
        if not self._is_slug_unique(slug, self._tag_slugs):
            raise ValidationError(f"validation.not_unique:slug={slug}")
        tag = Tag(id=uuid.uuid4(), name=name, slug=slug)
        tag.validate()
        self._tags[tag.id]=tag
        self._tag_slugs[slug]=tag.id
        return tag

    def list_tags(self) -> List[Tag]:
        return list(self._tags.values())

    # ---- Item CRUD ----
    def create_item(self, user: UserContext, title: str, slug: str, content: str, category_id: uuid.UUID, tag_ids: Optional[List[uuid.UUID]]=None) -> Item:
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
        item = Item(id=uuid.uuid4(), title=title, slug=slug, content=content, category_id=category_id, tag_ids=tag_ids or [], author_id=uuid.UUID(user.user_id) if self._is_uuid(user.user_id) else None)
        try:
            item.validate_for_draft()
        except ValueError as e:
            raise ValidationError(str(e))
        self._items[item.id]=item
        self._item_slugs[slug]=item.id
        return item

    def update_item_content(self, user: UserContext, item_id: uuid.UUID, title: Optional[str]=None, content: Optional[str]=None, slug: Optional[str]=None) -> Item:
        self._require_role(user, [UserRole.ADMIN, UserRole.EDITOR])
        item = self._get_item(item_id)
        if slug and slug != item.slug:
            slug = slug.strip().lower()
            if not SLUG_RE.match(slug):
                raise ValidationError(f"validation.invalid_slug_format:slug={slug}")
            if not self._is_slug_unique(slug, self._item_slugs, exclude_id=item.id):
                raise ValidationError(f"validation.not_unique:slug={slug}")
            # update index
            del self._item_slugs[item.slug]
            self._item_slugs[slug]=item.id
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

    def _is_uuid(self, s: str) -> bool:
        try:
            uuid.UUID(s)
            return True
        except:
            return False

    def _get_item(self, item_id: uuid.UUID) -> Item:
        if item_id not in self._items:
            raise NotFoundError(f"Item {item_id} not found")
        return self._items[item_id]

    # ---- Workflow ----
    def publish_item(self, user: UserContext, item_id: uuid.UUID) -> Item:
        self._require_role(user, [UserRole.ADMIN, UserRole.EDITOR])
        item = self._get_item(item_id)
        try:
            item.publish()
        except (ValueError, InvalidStateTransitionError) as e:
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
        self._items[dup.id]=dup
        self._item_slugs[dup.slug]=dup.id
        return dup

    # ---- Public read: only PUBLISHED ----
    def get_published_by_slug(self, slug: str) -> Item:
        slug = slug.strip().lower()
        item_id = self._item_slugs.get(slug)
        if not item_id:
            raise NotFoundError(f"Item slug {slug} not found")
        item = self._items[item_id]
        if not item.is_published():
            raise NotFoundError(f"Item {slug} not published - public cannot read")
        return item

    def list_published(self, category_id: Optional[uuid.UUID]=None, tag_id: Optional[uuid.UUID]=None) -> List[Item]:
        result = [i for i in self._items.values() if i.is_published()]
        if category_id:
            result = [i for i in result if i.category_id == category_id]
        if tag_id:
            result = [i for i in result if tag_id in i.tag_ids]
        return result

    def search_published(self, query: str) -> List[Item]:
        q = query.lower()
        return [i for i in self.list_published() if q in i.title.lower() or q in i.content.lower() or q in i.slug.lower()]

    # ---- Admin read: any status ----
    def list_all_items(self, user: UserContext, status: Optional[ItemStatus]=None) -> List[Item]:
        self._require_role(user, [UserRole.ADMIN, UserRole.EDITOR])
        items = list(self._items.values())
        if status:
            items = [i for i in items if i.status == status]
        return items

    def search_items(self, user: UserContext, query: str, only_published=False) -> List[Item]:
        self._require_role(user, [UserRole.ADMIN, UserRole.EDITOR])
        q = query.lower()
        items = self._items.values()
        if only_published:
            items = [i for i in items if i.is_published()]
        return [i for i in items if q in i.title.lower() or q in i.content.lower()]

    def get_item_admin(self, user: UserContext, item_id: uuid.UUID) -> Item:
        self._require_role(user, [UserRole.ADMIN, UserRole.EDITOR])
        return self._get_item(item_id)
