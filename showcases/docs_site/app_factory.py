from __future__ import annotations
from fastapi import FastAPI, HTTPException
from typing import Optional, Dict, List
import uuid, pathlib

from .services.docs_service import DocsService, NotFoundError, ValidationError
from .services.docs_renderer import DocsRenderer
from .services.docs_site_generator import DocsSiteGenerator
from .domain.models import SeoMeta
from ai_framework.rendering import GeneratedPage

FROZEN_ROUTES = {
    "POST /sections",
    "GET /sections",
    "POST /versions",
    "GET /versions",
    "POST /docs",
    "GET /docs",
    "PATCH /docs/{doc_id}/seo",
    "POST /docs/{doc_id}/publish",
    "GET /public/docs/{slug}",
    "GET /public/docs",
    "POST /site/generate",
    "GET /site/pages",
    "GET /site/pages/{path}",
    "GET /sitemap.xml",
}


def _to_dict(obj):
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return obj


def _parse_uuid(s: str) -> uuid.UUID:
    try:
        return uuid.UUID(s)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid UUID {s}")


def create_app(
    service: Optional[DocsService] = None, out_dir: pathlib.Path | None = None
) -> FastAPI:
    svc = service or DocsService()
    renderer = DocsRenderer()
    generator = DocsSiteGenerator(svc, renderer)
    out = out_dir or pathlib.Path("showcases/docs_site/output")
    state: Dict[str, List[GeneratedPage]] = {"pages": []}

    app = FastAPI(title="Docs Site — Type B Static/Generated")

    @app.post("/sections")
    def create_section(payload: dict):
        try:
            sec = svc.create_section(
                payload["name"], payload["slug"], payload.get("description", "")
            )
            return _to_dict(sec)
        except ValidationError as e:
            raise HTTPException(400, str(e))

    @app.get("/sections")
    def list_sections():
        return [_to_dict(s) for s in svc.list_sections()]

    @app.post("/versions")
    def create_version(payload: dict):
        try:
            ver = svc.create_version(payload["name"], payload["slug"])
            return _to_dict(ver)
        except ValidationError as e:
            raise HTTPException(400, str(e))

    @app.get("/versions")
    def list_versions():
        return [_to_dict(v) for v in svc.list_versions()]

    @app.post("/docs")
    def create_doc(payload: dict):
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
            sec_id = (
                _parse_uuid(payload["section_id"])
                if payload.get("section_id")
                else None
            )
            ver_id = (
                _parse_uuid(payload["version_id"])
                if payload.get("version_id")
                else None
            )
            doc = svc.create_page(
                payload["title"],
                payload["slug"],
                payload["content"],
                sec_id,
                ver_id,
                seo,
            )
            return _to_dict(doc)
        except NotFoundError as e:
            raise HTTPException(404, str(e))
        except ValidationError as e:
            raise HTTPException(400, str(e))

    @app.get("/docs")
    def list_docs():
        return [_to_dict(d) for d in svc.list_pages()]

    @app.patch("/docs/{doc_id}/seo")
    def update_seo(doc_id: str, payload: dict):
        try:
            seo = SeoMeta(
                payload.get("seo_title"),
                payload.get("seo_description"),
                payload.get("og_title"),
                payload.get("og_description"),
                payload.get("canonical_url"),
            )
            doc = svc.update_page_seo(_parse_uuid(doc_id), seo)
            return _to_dict(doc)
        except NotFoundError as e:
            raise HTTPException(404, str(e))

    @app.post("/docs/{doc_id}/publish")
    def publish(doc_id: str):
        try:
            doc = svc.publish_page(_parse_uuid(doc_id))
            return _to_dict(doc)
        except NotFoundError as e:
            raise HTTPException(404, str(e))

    @app.get("/public/docs/{slug}")
    def get_public(slug: str):
        try:
            return _to_dict(svc.get_published_by_slug(slug))
        except NotFoundError as e:
            raise HTTPException(404, str(e))

    @app.get("/public/docs")
    def list_public(section: Optional[str] = None, version: Optional[str] = None):
        return [_to_dict(p) for p in svc.list_published(section, version)]

    @app.post("/site/generate")
    def generate_site():
        pages = generator.generate()
        generator.write(pages, out)
        state["pages"] = pages
        return {
            "generated": len(pages),
            "out_dir": str(out),
            "pages": [p.path for p in pages],
        }

    @app.get("/site/pages")
    def list_pages():
        return [{"path": p.path, "kind": p.kind} for p in state["pages"]]

    @app.get("/site/pages/{path:path}")
    def get_page(path: str):
        for p in state["pages"]:
            if p.path == path:
                return {"path": p.path, "html": p.html}
        raise HTTPException(404, f"page {path} not generated")

    @app.get("/sitemap.xml")
    def sitemap():
        pages = state["pages"]
        if not pages:
            pages = generator.generate()
        for p in pages:
            if p.kind == "sitemap":
                return p.html
        return generator.renderer.render_sitemap(svc.list_published())

    app.state.frozen_routes = FROZEN_ROUTES
    app.state.service = svc
    app.state.generator = generator
    return app


def create_test_app() -> FastAPI:
    svc = DocsService()
    import tempfile

    tmp = pathlib.Path(tempfile.gettempdir()) / "docs_site_test_out"
    return create_app(service=svc, out_dir=tmp)
