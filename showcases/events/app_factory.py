from __future__ import annotations
import uuid
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ai_framework.rendering.static_writer import StaticSiteWriter
from showcases.events.services.events_service import (
    EventsService,
    NotFoundError,
    DuplicateSlugError,
    ValidationError,
    CapacityFullError,
)
from showcases.events.services.events_renderer import EventsRenderer
from showcases.events.services.events_site_generator import EventsSiteGenerator

FROZEN_ROUTES = [
    ("POST", "/venues"),
    ("GET", "/venues"),
    ("GET", "/venues/{id}"),
    ("POST", "/events"),
    ("GET", "/events"),
    ("GET", "/events/{id}"),
    ("PATCH", "/events/{id}"),
    ("PATCH", "/events/{id}/seo"),
    ("POST", "/events/{id}/publish"),
    ("POST", "/events/{id}/unpublish"),
    ("POST", "/events/{id}/cancel"),
    ("GET", "/public/events/{slug}"),
    ("POST", "/events/{id}/rsvp"),
    ("GET", "/events/{id}/rsvps"),
    ("POST", "/rsvps/{id}/cancel"),
    ("GET", "/rsvps/{id}"),
    ("POST", "/site/generate"),
    ("GET", "/site/pages"),
    ("GET", "/site/pages/{path:path}"),
    ("GET", "/sitemap.xml"),
]


class CreateVenueIn(BaseModel):
    name: str
    slug: str
    address: str = ""
    capacity: int | None = None


class CreateEventIn(BaseModel):
    title: str
    slug: str
    description: str
    venue_id: str
    start_time: str
    end_time: str
    capacity: int | None = None


class UpdateEventIn(BaseModel):
    title: str | None = None
    description: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    capacity: int | None = None


class UpdateSeoIn(BaseModel):
    seo_title: str | None = None
    seo_description: str | None = None
    canonical_url: str | None = None


class CreateRsvpIn(BaseModel):
    attendee_name: str


def _parse_uuid(v: str) -> uuid.UUID:
    try:
        return uuid.UUID(v)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {v}")


def _parse_dt(v: str) -> datetime:
    try:
        dt = datetime.fromisoformat(v)
        if dt.tzinfo is None:
            raise ValueError("must be timezone-aware")
        return dt
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid datetime {v}: {e}")


def _to_dict_venue(ven) -> Dict[str, Any]:
    return {
        "id": str(ven.id),
        "name": ven.name,
        "slug": ven.slug,
        "address": ven.address,
        "capacity": ven.capacity,
        "is_published": ven.is_published,
    }


def _to_dict_event(ev) -> Dict[str, Any]:
    return {
        "id": str(ev.id),
        "title": ev.title,
        "slug": ev.slug,
        "description": ev.description,
        "venue_id": str(ev.venue_id),
        "start_time": ev.start_time.isoformat(),
        "end_time": ev.end_time.isoformat(),
        "capacity": ev.capacity,
        "is_published": ev.is_published,
        "status": ev.status.value,
        "is_upcoming": ev.is_upcoming,
        "seo": {
            "seo_title": ev.seo.seo_title,
            "seo_description": ev.seo.seo_description,
            "canonical_url": ev.seo.canonical_url,
        }
        if ev.seo
        else None,
    }


def _to_dict_rsvp(r) -> Dict[str, Any]:
    return {
        "id": str(r.id),
        "event_id": str(r.event_id),
        "attendee_name": r.attendee_name,
        "status": r.status.value,
        "created_at": r.created_at,
    }


def create_app(
    service: EventsService | None = None, out_dir: str | Path | None = None
) -> FastAPI:
    service = service or EventsService()
    out_dir = Path(out_dir) if out_dir else Path("showcases/events/output")
    out_dir.mkdir(parents=True, exist_ok=True)

    renderer = EventsRenderer()
    generator = EventsSiteGenerator(service, renderer)
    writer = StaticSiteWriter()

    app = FastAPI(title="Events Vertical v0.1")
    app.state.events_service = service
    app.state.out_dir = out_dir
    app.state.generator = generator
    app.state.writer = writer
    app.state.pages: List[Dict[str, Any]] = []

    @app.post("/venues")
    def create_venue(payload: CreateVenueIn):
        try:
            v = service.create_venue(
                name=payload.name,
                slug=payload.slug,
                address=payload.address,
                capacity=payload.capacity,
            )
            return _to_dict_venue(v)
        except DuplicateSlugError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/venues")
    def list_venues():
        return [_to_dict_venue(v) for v in service.list_venues()]

    @app.get("/venues/{id}")
    def get_venue(id: str):
        try:
            vid = _parse_uuid(id)
            return _to_dict_venue(service.get_venue(vid))
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.post("/events")
    def create_event(payload: CreateEventIn):
        try:
            venue_id = _parse_uuid(payload.venue_id)
            st = _parse_dt(payload.start_time)
            et = _parse_dt(payload.end_time)
            ev = service.create_event(
                title=payload.title,
                slug=payload.slug,
                description=payload.description,
                venue_id=venue_id,
                start_time=st,
                end_time=et,
                capacity=payload.capacity,
            )
            return _to_dict_event(ev)
        except DuplicateSlugError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except (ValidationError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e))
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.get("/events")
    def list_events():
        return [_to_dict_event(e) for e in service.list_events()]

    @app.get("/events/{id}")
    def get_event(id: str):
        try:
            eid = _parse_uuid(id)
            return _to_dict_event(service.get_event(eid))
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.patch("/events/{id}")
    def update_event(id: str, payload: UpdateEventIn):
        try:
            eid = _parse_uuid(id)
            st = _parse_dt(payload.start_time) if payload.start_time else None
            et = _parse_dt(payload.end_time) if payload.end_time else None
            ev = service.update_event(
                eid,
                title=payload.title,
                description=payload.description,
                start_time=st,
                end_time=et,
                capacity=payload.capacity,
            )
            return _to_dict_event(ev)
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except (ValidationError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.patch("/events/{id}/seo")
    def update_seo(id: str, payload: UpdateSeoIn):
        try:
            eid = _parse_uuid(id)
            ev = service.update_seo(
                eid, payload.seo_title, payload.seo_description, payload.canonical_url
            )
            return _to_dict_event(ev)
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.post("/events/{id}/publish")
    def publish_event(id: str):
        try:
            eid = _parse_uuid(id)
            return _to_dict_event(service.publish(eid))
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except (ValidationError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/events/{id}/unpublish")
    def unpublish_event(id: str):
        try:
            eid = _parse_uuid(id)
            return _to_dict_event(service.unpublish(eid))
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.post("/events/{id}/cancel")
    def cancel_event(id: str):
        try:
            eid = _parse_uuid(id)
            return _to_dict_event(service.cancel(eid))
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.get("/public/events/{slug}")
    def get_public(slug: str):
        try:
            return _to_dict_event(service.get_published_by_slug(slug))
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.post("/events/{id}/rsvp")
    def create_rsvp(id: str, payload: CreateRsvpIn):
        try:
            eid = _parse_uuid(id)
            r = service.create_rsvp(eid, payload.attendee_name)
            return _to_dict_rsvp(r)
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except CapacityFullError as e:
            raise HTTPException(status_code=400, detail=f"FULL: {e}")

    @app.get("/events/{id}/rsvps")
    def list_rsvps(id: str):
        try:
            eid = _parse_uuid(id)
            service.get_event(eid)
            return [_to_dict_rsvp(r) for r in service.list_rsvps(eid)]
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.get("/rsvps/{id}")
    def get_rsvp(id: str):
        try:
            rid = _parse_uuid(id)
            return _to_dict_rsvp(service.get_rsvp(rid))
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.post("/rsvps/{id}/cancel")
    def cancel_rsvp(id: str):
        try:
            rid = _parse_uuid(id)
            return _to_dict_rsvp(service.cancel_rsvp(rid))
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.post("/site/generate")
    def generate_site():
        try:
            pages = generator.generate()
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
        target = out_dir / path
        if not target.exists() or not target.is_file():
            raise HTTPException(status_code=404, detail=f"Page {path} not found")
        return {"path": path, "content": target.read_text(encoding="utf-8")[:5000]}

    @app.get("/sitemap.xml")
    def get_sitemap():
        from fastapi.responses import Response

        target = out_dir / "sitemap.xml"
        if not target.exists():
            pages = generator.generate()
            content = renderer.render_sitemap(pages)
        else:
            content = target.read_text(encoding="utf-8")
        return Response(content=content, media_type="application/xml")

    return app
