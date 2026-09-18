from typing import Dict, List, Optional
import uuid
from showcases.cms_lite.domain.category import Category
from showcases.cms_lite.domain.item import Item
from showcases.cms_lite.domain.media import Media
from showcases.cms_lite.domain.item_status import ItemStatus
class NotFoundError(Exception): pass
class CmsLiteService:
    def __init__(self):
        self._categories: Dict[uuid.UUID, Category] = {}
        self._items: Dict[uuid.UUID, Item] = {}
        self._media: Dict[uuid.UUID, Media] = {}
    def create_category(self, name: str, slug: str, description: Optional[str]=None) -> Category:
        cat = Category(id=uuid.uuid4(), name=name, slug=slug, description=description)
        cat.validate()
        self._categories[cat.id]=cat
        return cat
    def create_item(self, title: str, slug: str, content: str, category_id: uuid.UUID) -> Item:
        if category_id not in self._categories:
            raise NotFoundError(f"Category {category_id} not found")
        item = Item(id=uuid.uuid4(), title=title, slug=slug, content=content, category_id=category_id)
        self._items[item.id]=item
        return item
    def publish_item(self, item_id: uuid.UUID) -> Item:
        item = self._items[item_id]
        item.publish()
        return item
    def unpublish_item(self, item_id: uuid.UUID) -> Item:
        item = self._items[item_id]
        item.unpublish()
        return item
    def duplicate_item(self, item_id: uuid.UUID) -> Item:
        src = self._items[item_id]
        dup = Item(id=uuid.uuid4(), title=f"{src.title} (copy)", slug=f"{src.slug}-copy-{str(uuid.uuid4())[:8]}", content=src.content, category_id=src.category_id, status=ItemStatus.DRAFT, tag_ids=list(src.tag_ids))
        self._items[dup.id]=dup
        return dup
    def search_items(self, query: str, only_published=False) -> List[Item]:
        q=query.lower()
        return [i for i in self._items.values() if (not only_published or i.is_published()) and (q in i.title.lower() or q in i.content.lower())]
    def list_published(self): return [i for i in self._items.values() if i.is_published()]
