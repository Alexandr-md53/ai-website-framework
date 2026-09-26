"""
Cafe Vertical v0.1 — App Factory — showcase-local, Type C runnable
FROZEN_ROUTES pattern like docs_site, no framework changes

Architecture:
- Uses CafeMenuService (Dict + slug index)
- Uses CafeRenderer (JinjaTemplateRenderer + SeoInjector)
- Uses CafeSiteGenerator (GeneratedPage)
- StaticSiteWriter is sole FS boundary
- No BaseService, no GenericRepository, no new abstraction

Publishable gate: cafe-local lifecycle DRAFT/PUBLISHED, not framework Publishable
Slug: validated via domain models_v01 (same regex as framework)
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ai_framework.rendering.static_writer import StaticSiteWriter
from showcases.cafe.services.cafe_menu_service import (
    CafeMenuService,
    NotFoundError,
    DuplicateSlugError,
    ValidationError,
    OutOfStockError,
    InsufficientStockError,
)
from showcases.cafe.services.cafe_renderer import CafeRenderer
from showcases.cafe.services.cafe_site_generator import CafeSiteGenerator


# ---- FROZEN ROUTES v0.1 ----
FROZEN_ROUTES = [
    ("POST", "/menu/categories"),
    ("GET", "/menu/categories"),
    ("POST", "/menu/items"),
    ("GET", "/menu/items"),
    ("GET", "/menu/items/{id}"),
    ("PATCH", "/menu/items/{id}"),
    ("PATCH", "/menu/items/{id}/seo"),
    ("POST", "/menu/items/{id}/publish"),
    ("POST", "/menu/items/{id}/unpublish"),
    ("PATCH", "/menu/items/{id}/availability"),
    ("POST", "/orders"),
    ("GET", "/orders"),
    ("GET", "/orders/{id}"),
    ("POST", "/orders/{id}/validate"),
    ("POST", "/orders/{id}/confirm"),
    ("POST", "/orders/{id}/cancel"),
    ("POST", "/site/generate"),
    ("GET", "/site/pages"),
    ("GET", "/site/pages/{path:path}"),
    ("GET", "/public/menu/{slug}"),
    ("GET", "/sitemap.xml"),
]

# ---- Pydantic DTOs ----


class CreateCategoryIn(BaseModel):
    name: str
    slug: str


class CreateItemIn(BaseModel):
    title: str
    slug: str
    description: str
    price: str  # Decimal as string
    category_id: str
    stock_quantity: int | None = None
    dietary_tags: List[str] | None = None


class UpdateItemIn(BaseModel):
    title: str | None = None
    description: str | None = None
    price: str | None = None
    stock_quantity: int | None = None
    category_id: str | None = None


class UpdateSeoIn(BaseModel):
    seo_title: str | None = None
    seo_description: str | None = None
    canonical_url: str | None = None


class SetAvailabilityIn(BaseModel):
    stock_quantity: int | None = None


class CreateOrderLineIn(BaseModel):
    menu_item_id: str
    quantity: int


class CreateOrderIn(BaseModel):
    lines: List[CreateOrderLineIn]


def _parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {value}")


def _to_dict_category(cat) -> Dict[str, Any]:
    return {
        "id": str(cat.id),
        "name": cat.name,
        "slug": cat.slug,
        "is_published": cat.is_published,
    }


def _to_dict_item(item) -> Dict[str, Any]:
    return {
        "id": str(item.id),
        "title": item.title,
        "slug": item.slug,
        "description": item.description,
        "price": str(item.price),
        "category_id": str(item.category_id),
        "stock_quantity": item.stock_quantity,
        "is_published": item.is_published,
        "is_available": item.is_available,
        "status": item.status.value,
        "seo": {
            "seo_title": item.seo.seo_title,
            "seo_description": item.seo.seo_description,
            "canonical_url": item.seo.canonical_url,
        }
        if item.seo
        else None,
        "dietary_tags": item.dietary_tags,
    }


def _to_dict_order(order) -> Dict[str, Any]:
    return {
        "id": str(order.id),
        "lines": [
            {
                "menu_item_id": str(l.menu_item_id),
                "quantity": l.quantity,
                "price_snapshot": str(l.price_snapshot),
            }
            for l in order.lines
        ],
        "total": str(order.total),
        "status": order.status.value,
        "created_at": order.created_at,
    }


def create_app(
    service: CafeMenuService | None = None, out_dir: str | Path | None = None
) -> FastAPI:
    service = service or CafeMenuService()
    out_dir = Path(out_dir) if out_dir else Path("showcases/cafe/output")
    out_dir.mkdir(parents=True, exist_ok=True)

    renderer = CafeRenderer()
    generator = CafeSiteGenerator(service, renderer)
    writer = StaticSiteWriter()

    app = FastAPI(title="Cafe Vertical v0.1")
    app.state.cafe_service = service
    app.state.out_dir = out_dir
    app.state.generator = generator
    app.state.writer = writer
    app.state.pages: List[Dict[str, Any]] = []  # cache like blog_cms/docs_site

    # ---- Category ----
    @app.post("/menu/categories")
    def create_category(payload: CreateCategoryIn):
        try:
            cat = service.create_category(name=payload.name, slug=payload.slug)
            return _to_dict_category(cat)
        except DuplicateSlugError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/menu/categories")
    def list_categories():
        return [_to_dict_category(c) for c in service.list_categories()]

    # ---- Menu Items ----
    @app.post("/menu/items")
    def create_item(payload: CreateItemIn):
        try:
            cat_id = _parse_uuid(payload.category_id)
            price = Decimal(payload.price)
            item = service.create_item(
                title=payload.title,
                slug=payload.slug,
                description=payload.description,
                price=price,
                category_id=cat_id,
                stock_quantity=payload.stock_quantity,
                dietary_tags=payload.dietary_tags,
            )
            return _to_dict_item(item)
        except DuplicateSlugError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except (ValueError, ValidationError) as e:
            raise HTTPException(status_code=400, detail=str(e))
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.get("/menu/items")
    def list_items(published: bool | None = None, category: str | None = None):
        if published:
            items = service.list_published(category_slug=category)
        else:
            items = service.list_items()
            if category:
                # filter by category slug
                from showcases.cafe.services.cafe_menu_service import (
                    CafeMenuService as S,
                )

                # find cat id
                for c in service.list_categories():
                    if c.slug == category:
                        items = [i for i in items if i.category_id == c.id]
                        break
                else:
                    items = []
        return [_to_dict_item(i) for i in items]

    @app.get("/menu/items/{id}")
    def get_item(id: str):
        try:
            item_id = _parse_uuid(id)
            item = service.get_item(item_id)
            return _to_dict_item(item)
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.patch("/menu/items/{id}")
    def update_item(id: str, payload: UpdateItemIn):
        try:
            item_id = _parse_uuid(id)
            price = Decimal(payload.price) if payload.price is not None else None
            cat_id = _parse_uuid(payload.category_id) if payload.category_id else None
            item = service.update_item(
                item_id,
                title=payload.title,
                description=payload.description,
                price=price,
                stock_quantity=payload.stock_quantity,
                category_id=cat_id,
            )
            return _to_dict_item(item)
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except (ValueError, ValidationError) as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.patch("/menu/items/{id}/seo")
    def update_seo(id: str, payload: UpdateSeoIn):
        try:
            item_id = _parse_uuid(id)
            item = service.update_seo(
                item_id,
                payload.seo_title,
                payload.seo_description,
                payload.canonical_url,
            )
            return _to_dict_item(item)
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.post("/menu/items/{id}/publish")
    def publish_item(id: str):
        try:
            item_id = _parse_uuid(id)
            item = service.publish(item_id)
            return _to_dict_item(item)
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except (ValueError, ValidationError) as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/menu/items/{id}/unpublish")
    def unpublish_item(id: str):
        try:
            item_id = _parse_uuid(id)
            item = service.unpublish(item_id)
            return _to_dict_item(item)
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.patch("/menu/items/{id}/availability")
    def set_availability(id: str, payload: SetAvailabilityIn):
        try:
            item_id = _parse_uuid(id)
            item = service.set_availability(item_id, payload.stock_quantity)
            return _to_dict_item(item)
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except (ValueError, ValidationError) as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/public/menu/{slug}")
    def get_public_by_slug(slug: str):
        try:
            item = service.get_published_by_slug(slug)
            return _to_dict_item(item)
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # ---- Orders ----
    @app.post("/orders")
    def create_order(payload: CreateOrderIn):
        try:
            lines = [
                {"menu_item_id": l.menu_item_id, "quantity": l.quantity}
                for l in payload.lines
            ]
            order = service.create_order(lines)
            return _to_dict_order(order)
        except (ValidationError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e))
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except OutOfStockError as e:
            raise HTTPException(status_code=400, detail=f"OUT_OF_STOCK: {e}")
        except InsufficientStockError as e:
            raise HTTPException(status_code=400, detail=f"INSUFFICIENT_STOCK: {e}")

    @app.get("/orders")
    def list_orders():
        return [_to_dict_order(o) for o in service.list_orders()]

    @app.get("/orders/{id}")
    def get_order(id: str):
        try:
            oid = _parse_uuid(id)
            order = service.get_order(oid)
            return _to_dict_order(order)
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.post("/orders/{id}/validate")
    def validate_order(id: str):
        try:
            oid = _parse_uuid(id)
            order = service.validate_order(oid)
            return _to_dict_order(order)
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except (ValidationError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e))
        except OutOfStockError as e:
            raise HTTPException(status_code=400, detail=f"OUT_OF_STOCK: {e}")
        except InsufficientStockError as e:
            raise HTTPException(status_code=400, detail=f"INSUFFICIENT_STOCK: {e}")

    @app.post("/orders/{id}/confirm")
    def confirm_order(id: str):
        try:
            oid = _parse_uuid(id)
            order = service.confirm_order(oid)
            return _to_dict_order(order)
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except (ValidationError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e))
        except OutOfStockError as e:
            raise HTTPException(status_code=400, detail=f"OUT_OF_STOCK: {e}")
        except InsufficientStockError as e:
            raise HTTPException(status_code=400, detail=f"INSUFFICIENT_STOCK: {e}")

    @app.post("/orders/{id}/cancel")
    def cancel_order(id: str):
        try:
            oid = _parse_uuid(id)
            order = service.cancel_order(oid)
            return _to_dict_order(order)
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # ---- Site generation ----
    @app.post("/site/generate")
    def generate_site():
        try:
            pages = generator.generate()
            # write via StaticSiteWriter — sole FS boundary
            writer.write(pages, out_dir, clean=True)
            app.state.pages = [{"path": p.path, "kind": p.kind} for p in pages]
            return {"generated": len(pages), "pages": app.state.pages}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/site/pages")
    def get_pages():
        return app.state.pages

    @app.get("/site/pages/{path:path}")
    def get_page_by_path(path: str):
        # return file content if exists
        target = out_dir / path
        if not target.exists() or not target.is_file():
            raise HTTPException(status_code=404, detail=f"Page {path} not found")
        return {"path": path, "content": target.read_text(encoding="utf-8")[:5000]}

    @app.get("/sitemap.xml")
    def get_sitemap():
        from fastapi.responses import Response

        target = out_dir / "sitemap.xml"
        if not target.exists():
            # generate on fly from pages state
            pages = generator.generate()
            content = renderer.render_sitemap(pages)
        else:
            content = target.read_text(encoding="utf-8")
        return Response(content=content, media_type="application/xml")

    return app
