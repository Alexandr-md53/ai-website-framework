from __future__ import annotations
import uuid, re
from typing import Dict, List, Optional
from ..domain.models import Post, Category, Tag, Author, PostStatus, SeoMeta, SLUG_RE
from ..domain.user import UserContext, UserRole, PermissionDeniedError, PipelineContext


class NotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass


class BlogCmsService:
    """Type B domain service — in-memory, deterministic, no DB"""

    def __init__(self):
        self._categories: Dict[uuid.UUID, Category] = {}
        self._tags: Dict[uuid.UUID, Tag] = {}
        self._authors: Dict[uuid.UUID, Author] = {}
        self._posts: Dict[uuid.UUID, Post] = {}
        self._slugs: Dict[str, Dict[str, uuid.UUID]] = {
            "category": {},
            "tag": {},
            "author": {},
            "post": {},
        }

    # ---- Guards ----
    def _require(self, ctx: PipelineContext, allowed: List[UserRole]):
        if ctx.user.role not in allowed:
            raise PermissionDeniedError(f"Forbidden: {ctx.user.role} not in {allowed}")

    def _uniq(self, kind: str, slug: str, exclude: Optional[uuid.UUID] = None) -> bool:
        idx = self._slugs[kind]
        if slug not in idx:
            return True
        return idx[slug] == exclude if exclude else False

    # ---- Category / Tag / Author ----
    def create_category(
        self,
        ctx: PipelineContext,
        name: str,
        slug: str,
        description: Optional[str] = None,
    ) -> Category:
        self._require(ctx, [UserRole.ADMIN, UserRole.EDITOR])
        slug = slug.lower().strip()
        if not SLUG_RE.match(slug):
            raise ValidationError(f"invalid slug {slug}")
        if not self._uniq("category", slug):
            raise ValidationError(f"not unique {slug}")
        cat = Category(id=uuid.uuid4(), name=name, slug=slug, description=description)
        cat.validate()
        self._categories[cat.id] = cat
        self._slugs["category"][slug] = cat.id
        return cat

    def create_tag(self, ctx: PipelineContext, name: str, slug: str) -> Tag:
        self._require(ctx, [UserRole.ADMIN, UserRole.EDITOR])
        slug = slug.lower().strip()
        if not SLUG_RE.match(slug):
            raise ValidationError(f"invalid slug {slug}")
        if not self._uniq("tag", slug):
            raise ValidationError(f"not unique {slug}")
        tag = Tag(id=uuid.uuid4(), name=name, slug=slug)
        tag.validate()
        self._tags[tag.id] = tag
        self._slugs["tag"][slug] = tag.id
        return tag

    def create_author(
        self, ctx: PipelineContext, name: str, slug: str, bio: Optional[str] = None
    ) -> Author:
        self._require(ctx, [UserRole.ADMIN, UserRole.EDITOR])
        slug = slug.lower().strip()
        if not SLUG_RE.match(slug):
            raise ValidationError(f"invalid slug {slug}")
        if not self._uniq("author", slug):
            raise ValidationError(f"not unique {slug}")
        a = Author(id=uuid.uuid4(), name=name, slug=slug, bio=bio)
        a.validate()
        self._authors[a.id] = a
        self._slugs["author"][slug] = a.id
        return a

    # ---- Post CRUD + Workflow ----
    def create_post(
        self,
        ctx: PipelineContext,
        title: str,
        slug: str,
        content: str,
        category_id: uuid.UUID,
        author_id: uuid.UUID,
        tag_ids: Optional[List[uuid.UUID]] = None,
        seo: Optional[SeoMeta] = None,
    ) -> Post:
        self._require(ctx, [UserRole.ADMIN, UserRole.EDITOR])
        slug = slug.lower().strip()
        if not SLUG_RE.match(slug):
            raise ValidationError(f"invalid slug {slug}")
        if not self._uniq("post", slug):
            raise ValidationError(f"not unique {slug}")
        if category_id not in self._categories:
            raise NotFoundError("category not found")
        if author_id not in self._authors:
            raise NotFoundError("author not found")
        if tag_ids:
            for tid in tag_ids:
                if tid not in self._tags:
                    raise NotFoundError(f"tag {tid} not found")
        post = Post(
            id=uuid.uuid4(),
            title=title,
            slug=slug,
            content=content,
            category_id=category_id,
            author_id=author_id,
            tag_ids=tag_ids or [],
            seo=seo or SeoMeta(),
        )
        post.validate_for_draft()
        self._posts[post.id] = post
        self._slugs["post"][slug] = post.id
        return post

    def update_post_seo(
        self, ctx: PipelineContext, post_id: uuid.UUID, seo: SeoMeta
    ) -> Post:
        self._require(ctx, [UserRole.ADMIN, UserRole.EDITOR])
        post = self._get_post(post_id)
        seo.validate()
        post.seo = seo
        return post

    def publish_post(self, ctx: PipelineContext, post_id: uuid.UUID) -> Post:
        self._require(ctx, [UserRole.ADMIN, UserRole.EDITOR, UserRole.GENERATOR])
        post = self._get_post(post_id)
        post.publish()
        return post

    def unpublish_post(self, ctx: PipelineContext, post_id: uuid.UUID) -> Post:
        self._require(ctx, [UserRole.ADMIN, UserRole.EDITOR])
        post = self._get_post(post_id)
        post.unpublish()
        return post

    def duplicate_post(self, ctx: PipelineContext, post_id: uuid.UUID) -> Post:
        self._require(ctx, [UserRole.ADMIN, UserRole.EDITOR])
        src = self._get_post(post_id)
        base = f"{src.slug}-copy"
        cand = base
        c = 1
        while not self._uniq("post", cand):
            c += 1
            cand = f"{base}-{c}"
        dup = Post(
            id=uuid.uuid4(),
            title=f"{src.title} (copy)",
            slug=cand,
            content=src.content,
            category_id=src.category_id,
            author_id=src.author_id,
            tag_ids=list(src.tag_ids),
            status=PostStatus.DRAFT,
            seo=src.seo,
        )
        self._posts[dup.id] = dup
        self._slugs["post"][cand] = dup.id
        return dup

    def _get_post(self, pid: uuid.UUID) -> Post:
        if pid not in self._posts:
            raise NotFoundError(f"post {pid} not found")
        return self._posts[pid]

    # Public read (published only)
    def get_published_by_slug(self, slug: str) -> Post:
        slug = slug.lower().strip()
        pid = self._slugs["post"].get(slug)
        if not pid:
            raise NotFoundError(f"slug {slug} not found")
        p = self._posts[pid]
        if not p.is_published():
            raise NotFoundError(f"{slug} not published")
        return p

    def list_published(
        self, category_slug: Optional[str] = None, tag_slug: Optional[str] = None
    ) -> List[Post]:
        res = [p for p in self._posts.values() if p.is_published()]
        if category_slug:
            cid = self._slugs["category"].get(category_slug)
            res = [p for p in res if p.category_id == cid] if cid else []
        if tag_slug:
            tid = self._slugs["tag"].get(tag_slug)
            res = [p for p in res if tid in p.tag_ids] if tid else []
        return res

    def list_categories(self):
        return list(self._categories.values())

    def list_tags(self):
        return list(self._tags.values())

    def list_authors(self):
        return list(self._authors.values())

    def list_posts(self, status: Optional[PostStatus] = None):
        if status:
            return [p for p in self._posts.values() if p.status == status]
        return list(self._posts.values())
