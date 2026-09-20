from __future__ import annotations
from fastapi import FastAPI, HTTPException, Header, Depends
from typing import Optional, Dict, List
import uuid, pathlib

from .domain.user import PipelineContext, UserRole
from .domain.models import SeoMeta
from .services.blog_service import (
    BlogCmsService,
    NotFoundError,
    ValidationError,
    PermissionDeniedError,
)
from .services.site_generator import SiteGenerator, Renderer, GeneratedPage

# ---------- Frozen Route Map (single source of truth) ----------
# NOTE: param names must match actual FastAPI paths ({post_id} not {id}, {path} normalized from {path:path})
FROZEN_ROUTES = {
    # CRUD
    "POST /categories",
    "GET /categories",
    "POST /tags",
    "GET /tags",
    "POST /authors",
    "GET /authors",
    "POST /posts",
    "GET /posts",
    "PATCH /posts/{post_id}/seo",
    "POST /posts/{post_id}/publish",
    "POST /posts/{post_id}/unpublish",
    "POST /posts/{post_id}/duplicate",
    # Public
    "GET /public/posts/{slug}",
    "GET /public/posts",
    # Generation (Type B specific)
    "POST /site/generate",
    "GET /site/pages",
    "GET /site/pages/{path}",
    # Meta
    "GET /rss.xml",
    "GET /sitemap.xml",
}


def _ctx_from_headers(
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(default=None, alias="X-User-Role"),
) -> PipelineContext:
    # Unified boundary normalization — only place that reads headers
    return PipelineContext.from_raw(x_user_id, x_user_role)


def _to_dict(obj):
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "__dict__"):
        d = {}
        for k, v in obj.__dict__.items():
            if not k.startswith("_"):
                if isinstance(v, uuid.UUID):
                    v = str(v)
                if hasattr(v, "value"):
                    v = v.value
                d[k] = v
        return d
    return obj


def _parse_uuid(s: str) -> uuid.UUID:
    try:
        return uuid.UUID(s)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid UUID {s}")


def create_app(
    service: Optional[BlogCmsService] = None, out_dir: pathlib.Path | None = None
) -> FastAPI:
    svc = service or BlogCmsService()
    renderer = Renderer()
    generator = SiteGenerator(svc, renderer)
    out = out_dir or pathlib.Path("showcases/blog_cms/output")
    # in-memory cache of last generation
    state: Dict[str, List[GeneratedPage]] = {"pages": []}

    app = FastAPI(title="Blog CMS — Type B Static/Generated")

    # ---- Admin ----
    @app.post("/categories")
    def create_category(
        payload: dict, ctx: PipelineContext = Depends(_ctx_from_headers)
    ):
        try:
            cat = svc.create_category(
                ctx, payload["name"], payload["slug"], payload.get("description")
            )
            return _to_dict(cat)
        except PermissionDeniedError as e:
            raise HTTPException(403, str(e))
        except (ValidationError, ValueError) as e:
            raise HTTPException(400, str(e))

    @app.get("/categories")
    def list_categories():
        return [_to_dict(c) for c in svc.list_categories()]

    @app.post("/tags")
    def create_tag(payload: dict, ctx: PipelineContext = Depends(_ctx_from_headers)):
        try:
            tag = svc.create_tag(ctx, payload["name"], payload["slug"])
            return _to_dict(tag)
        except PermissionDeniedError as e:
            raise HTTPException(403, str(e))
        except (ValidationError, ValueError) as e:
            raise HTTPException(400, str(e))

    @app.get("/tags")
    def list_tags():
        return [_to_dict(t) for t in svc.list_tags()]

    @app.post("/authors")
    def create_author(payload: dict, ctx: PipelineContext = Depends(_ctx_from_headers)):
        try:
            a = svc.create_author(
                ctx, payload["name"], payload["slug"], payload.get("bio")
            )
            return _to_dict(a)
        except PermissionDeniedError as e:
            raise HTTPException(403, str(e))
        except (ValidationError, ValueError) as e:
            raise HTTPException(400, str(e))

    @app.get("/authors")
    def list_authors():
        return [_to_dict(a) for a in svc.list_authors()]

    @app.post("/posts")
    def create_post(payload: dict, ctx: PipelineContext = Depends(_ctx_from_headers)):
        try:
            seo = None
            if any(
                k in payload
                for k in [
                    "seo_title",
                    "seo_description",
                    "og_title",
                    "og_description",
                    "canonical_url",
                ]
            ):
                seo = SeoMeta(
                    payload.get("seo_title"),
                    payload.get("seo_description"),
                    payload.get("og_title"),
                    payload.get("og_description"),
                    payload.get("canonical_url"),
                )
            post = svc.create_post(
                ctx,
                payload["title"],
                payload["slug"],
                payload["content"],
                _parse_uuid(payload["category_id"]),
                _parse_uuid(payload["author_id"]),
                [_parse_uuid(t) for t in payload.get("tag_ids", [])],
                seo,
            )
            return _to_dict(post)
        except PermissionDeniedError as e:
            raise HTTPException(403, str(e))
        except NotFoundError as e:
            raise HTTPException(404, str(e))
        except (ValidationError, ValueError) as e:
            raise HTTPException(400, str(e))

    @app.get("/posts")
    def list_posts(status: Optional[str] = None):
        from .domain.models import PostStatus

        st = None
        if status:
            try:
                st = PostStatus(status.upper())
            except Exception:
                raise HTTPException(400, f"invalid status {status}")
        return [_to_dict(p) for p in svc.list_posts(st)]

    @app.patch("/posts/{post_id}/seo")
    def update_seo(
        post_id: str, payload: dict, ctx: PipelineContext = Depends(_ctx_from_headers)
    ):
        try:
            seo = SeoMeta(
                payload.get("seo_title"),
                payload.get("seo_description"),
                payload.get("og_title"),
                payload.get("og_description"),
                payload.get("canonical_url"),
            )
            post = svc.update_post_seo(ctx, _parse_uuid(post_id), seo)
            return _to_dict(post)
        except PermissionDeniedError as e:
            raise HTTPException(403, str(e))
        except NotFoundError as e:
            raise HTTPException(404, str(e))
        except (ValidationError, ValueError) as e:
            raise HTTPException(400, str(e))

    @app.post("/posts/{post_id}/publish")
    def publish(post_id: str, ctx: PipelineContext = Depends(_ctx_from_headers)):
        try:
            post = svc.publish_post(ctx, _parse_uuid(post_id))
            return _to_dict(post)
        except PermissionDeniedError as e:
            raise HTTPException(403, str(e))
        except NotFoundError as e:
            raise HTTPException(404, str(e))
        except (ValidationError, ValueError) as e:
            raise HTTPException(400, str(e))

    @app.post("/posts/{post_id}/unpublish")
    def unpublish(post_id: str, ctx: PipelineContext = Depends(_ctx_from_headers)):
        try:
            post = svc.unpublish_post(ctx, _parse_uuid(post_id))
            return _to_dict(post)
        except PermissionDeniedError as e:
            raise HTTPException(403, str(e))
        except NotFoundError as e:
            raise HTTPException(404, str(e))
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.post("/posts/{post_id}/duplicate")
    def duplicate(post_id: str, ctx: PipelineContext = Depends(_ctx_from_headers)):
        try:
            post = svc.duplicate_post(ctx, _parse_uuid(post_id))
            return _to_dict(post)
        except PermissionDeniedError as e:
            raise HTTPException(403, str(e))
        except NotFoundError as e:
            raise HTTPException(404, str(e))
        except Exception as e:
            raise HTTPException(400, str(e))

    # ---- Public ----
    @app.get("/public/posts/{slug}")
    def get_public(slug: str):
        try:
            return _to_dict(svc.get_published_by_slug(slug))
        except NotFoundError as e:
            raise HTTPException(404, str(e))

    @app.get("/public/posts")
    def list_public(category: Optional[str] = None, tag: Optional[str] = None):
        return [_to_dict(p) for p in svc.list_published(category, tag)]

    # ---- Generation Pipeline G1/G2/G12 ----
    @app.post("/site/generate")
    def generate_site(ctx: PipelineContext = Depends(_ctx_from_headers)):
        try:
            # Only ADMIN/EDITOR/GENERATOR can trigger build
            svc._require(ctx, [UserRole.ADMIN, UserRole.EDITOR, UserRole.GENERATOR])
            pages = generator.generate()
            generator.write(pages, out)
            state["pages"] = pages
            return {
                "generated": len(pages),
                "out_dir": str(out),
                "pages": [p.path for p in pages],
            }
        except PermissionDeniedError as e:
            raise HTTPException(403, str(e))

    @app.get("/site/pages")
    def list_pages():
        return [{"path": p.path, "kind": p.kind} for p in state["pages"]]

    @app.get("/site/pages/{path:path}")
    def get_page(path: str):
        # serve from last generation memory
        for p in state["pages"]:
            if p.path == path:
                return {"path": p.path, "html": p.html}
        raise HTTPException(404, f"page {path} not generated")

    @app.get("/rss.xml")
    def rss():
        pages = state["pages"]
        # if not generated, generate on fly
        if not pages:
            pages = generator.generate()
        for p in pages:
            if p.kind == "rss":
                return p.html
        return generator.renderer.render_rss(svc.list_published())

    @app.get("/sitemap.xml")
    def sitemap():
        pages = state["pages"]
        if not pages:
            pages = generator.generate()
        for p in pages:
            if p.kind == "sitemap":
                return p.html
        return generator.renderer.render_sitemap(svc.list_published())

    # expose frozen map for smoke test
    app.state.frozen_routes = FROZEN_ROUTES
    app.state.service = svc
    app.state.generator = generator
    return app


# ---- Dual factory ----
def create_test_app() -> FastAPI:
    """Deterministic test app — no FS side effects, fresh in-memory service"""
    svc = BlogCmsService()
    # use temp out dir
    import tempfile

    tmp = pathlib.Path(tempfile.gettempdir()) / "blog_cms_test_out"
    app = create_app(service=svc, out_dir=tmp)
    return app


def build_cms_lite_app(*args, **kwargs):  # alias for old tests compat if needed
    return create_app(*args, **kwargs)
