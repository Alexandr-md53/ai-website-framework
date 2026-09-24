from __future__ import annotations

import pathlib
import uuid
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException
from fastapi import Query as FastAPIQuery
from pydantic import BaseModel

from ai_framework.rendering import StaticSiteWriter

from .domain.models import SeoMeta
from .services.docs_service import DocsService
from .services.docs_renderer import DocsRenderer
from .services.docs_site_generator import DocsSiteGenerator


FROZEN_ROUTES = [
    "POST /sections",
    "GET /sections",
    "POST /versions",
    "GET /versions",
    "POST /docs",
    "GET /docs",
    "PATCH /docs/{id}/seo",
    "POST /docs/{id}/publish",
    "POST /docs/{id}/unpublish",
    "GET /public/pages/{slug}",
    "POST /site/generate",
    "GET /site/pages",
    "GET /site/pages/{path}",
]


def _to_uuid(v: str | uuid.UUID) -> uuid.UUID:
    if isinstance(v, uuid.UUID):
        return v
    try:
        return uuid.UUID(str(v))
    except Exception:
        raise HTTPException(status_code=400, detail=f"invalid uuid {v!r}")


def _section_to_dict(section) -> dict[str, Any]:
    return {
        "id": str(section.id),
        "name": section.name,
        "slug": section.slug,
        "description": section.description,
    }


def _version_to_dict(version) -> dict[str, Any]:
    return {
        "id": str(version.id),
        "name": version.name,
        "slug": version.slug,
    }


class SectionCreate(BaseModel):
    name: str
    slug: str
    description: str = ""


class VersionCreate(BaseModel):
    name: str
    slug: str


class DocCreate(BaseModel):
    title: str
    slug: str
    content: str
    section_id: str
    version_id: str


class SeoPatch(BaseModel):
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    canonical_url: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


def create_app(
    service: Optional[DocsService] = None,
    templates_dir: Optional[pathlib.Path | str] = None,
    out_dir: pathlib.Path | str = pathlib.Path("dist/docs_site"),
) -> FastAPI:
    if templates_dir is None:
        templates_dir = pathlib.Path(__file__).parent / "templates"

    docs_service = service or DocsService()
    renderer = DocsRenderer(templates_dir)
    generator = DocsSiteGenerator(docs_service, renderer)
    writer = StaticSiteWriter()

    app = FastAPI(title="docs_site showcase")
    generated_cache: Dict[str, Any] = {"pages": []}

    @app.post("/sections")
    def post_section(payload: SectionCreate):
        try:
            sec = docs_service.create_section(
                name=payload.name, slug=payload.slug, description=payload.description
            )
        except Exception as e:
            from .services.docs_service import ValidationError as SValidationError

            if isinstance(e, SValidationError):
                raise HTTPException(status_code=400, detail=str(e))
            raise
        return _section_to_dict(sec)

    @app.get("/sections")
    def get_sections():
        secs = docs_service.list_sections()
        return [_section_to_dict(s) for s in secs]

    @app.post("/versions")
    def post_version(payload: VersionCreate):
        try:
            ver = docs_service.create_version(name=payload.name, slug=payload.slug)
        except Exception as e:
            from .services.docs_service import ValidationError as SValidationError

            if isinstance(e, SValidationError):
                raise HTTPException(status_code=400, detail=str(e))
            raise
        return _version_to_dict(ver)

    @app.get("/versions")
    def get_versions():
        vers = docs_service.list_versions()
        return [_version_to_dict(v) for v in vers]

    @app.post("/docs")
    def post_doc(payload: DocCreate):
        try:
            sec_id = _to_uuid(payload.section_id)
            ver_id = _to_uuid(payload.version_id)
            page = docs_service.create_page(
                title=payload.title,
                slug=payload.slug,
                content=payload.content,
                section_id=sec_id,
                version_id=ver_id,
            )
        except Exception as e:
            from .services.docs_service import ValidationError, NotFoundError

            if isinstance(e, ValidationError):
                raise HTTPException(status_code=400, detail=str(e))
            if isinstance(e, NotFoundError):
                raise HTTPException(status_code=404, detail=str(e))
            raise
        return page.to_dict()

    @app.get("/docs")
    def get_docs():
        pages = docs_service.list_pages()
        return [p.to_dict() for p in pages]

    @app.patch("/docs/{id}/seo")
    def patch_docs_seo(id: str, payload: SeoPatch):
        pid = _to_uuid(id)
        seo = SeoMeta(
            seo_title=payload.seo_title or payload.title or "",
            seo_description=payload.seo_description or payload.description or "",
            canonical_url=payload.canonical_url or "",
            og_title=payload.og_title or payload.seo_title or payload.title or "",
            og_description=payload.og_description
            or payload.seo_description
            or payload.description
            or "",
        )
        try:
            page = docs_service.update_page_seo(pid, seo)
        except Exception as e:
            from .services.docs_service import NotFoundError

            if isinstance(e, NotFoundError):
                raise HTTPException(status_code=404, detail=str(e))
            raise
        return page.to_dict()

    @app.post("/docs/{id}/publish")
    def publish_docs(id: str):
        pid = _to_uuid(id)
        try:
            docs_service.publish(pid)
        except Exception as e:
            from .services.docs_service import ValidationError, NotFoundError

            if isinstance(e, NotFoundError):
                raise HTTPException(status_code=404, detail=str(e))
            if isinstance(e, ValidationError):
                raise HTTPException(status_code=400, detail=str(e))
            raise
        return {"id": id, "published": True}

    @app.post("/docs/{id}/unpublish")
    def unpublish_docs(id: str):
        pid = _to_uuid(id)
        try:
            docs_service.unpublish(pid)
        except Exception as e:
            from .services.docs_service import NotFoundError

            if isinstance(e, NotFoundError):
                raise HTTPException(status_code=404, detail=str(e))
            raise
        return {"id": id, "published": False}

    @app.post("/pages")
    def post_page_alias(payload: DocCreate):
        return post_doc(payload)

    @app.patch("/pages/{page_id}/seo")
    def patch_page_alias(page_id: str, payload: SeoPatch):
        return patch_docs_seo(page_id, payload)

    @app.post("/pages/{page_id}/publish")
    def publish_page_alias(page_id: str):
        return publish_docs(page_id)

    @app.post("/pages/{page_id}/unpublish")
    def unpublish_page_alias(page_id: str):
        return unpublish_docs(page_id)

    @app.get("/public/pages/{slug}")
    def get_public_page(slug: str, version: Optional[str] = FastAPIQuery(default=None)):
        try:
            page = docs_service.get_published_by_slug(slug, version)
            return {"page": page.to_dict(), "html": ""}
        except Exception as e:
            from .services.docs_service import NotFoundError

            if isinstance(e, NotFoundError):
                raise HTTPException(status_code=404, detail=str(e))
            raise

    @app.post("/site/generate")
    def site_generate():
        pages = generator.generate()
        try:
            written = writer.write(pages, out_dir, clean=True)
            written_str = [str(p) for p in written]
        except Exception:
            written_str = []
        generated_cache["pages"] = pages
        return {
            "generated": len(pages),
            "written": written_str,
            "paths": [p.path for p in pages],
        }

    @app.get("/site/pages")
    def site_pages():
        pages = generated_cache.get("pages")
        if not pages:
            pages = generator.generate()
            generated_cache["pages"] = pages
        return [{"path": p.path, "kind": p.kind} for p in pages]

    @app.get("/site/pages/{path:path}")
    def site_page_by_path(path: str):
        pages = generated_cache.get("pages")
        if not pages:
            pages = generator.generate()
            generated_cache["pages"] = pages
        target = next((p for p in pages if p.path == path), None)
        if not target:
            target = next((p for p in pages if p.path == f"{path}/index.html"), None)
        if not target:
            target = next(
                (p for p in pages if p.path.lstrip("/") == path.lstrip("/")), None
            )
        if not target:
            raise HTTPException(status_code=404, detail="generated page not found")
        return {
            "path": target.path,
            "kind": getattr(target, "kind", "page"),
            "html": getattr(target, "html", ""),
        }

    return app


def create_test_app(*args, **kwargs) -> FastAPI:
    return create_app(*args, **kwargs)


app = create_app()

__all__ = ["create_app", "create_test_app", "app", "FROZEN_ROUTES"]
