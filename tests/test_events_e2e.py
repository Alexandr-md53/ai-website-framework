from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
from datetime import datetime, UTC, timedelta

from showcases.events.app_factory import create_app, FROZEN_ROUTES
from showcases.events.services.events_service import EventsService
from ai_framework.rendering.jinja import JinjaTemplateRenderer
from ai_framework.rendering.seo import SeoInjector, SeoContext
from ai_framework.rendering.generated_page import GeneratedPage
from ai_framework.rendering.static_writer import StaticSiteWriter
from ai_framework.content.slug import Slug


def test_frozen_route_map_smoke():
    service = EventsService()
    with tempfile.TemporaryDirectory() as tmp:
        app = create_app(service=service, out_dir=tmp)
        actual = set()
        for route in app.routes:
            if hasattr(route, "methods") and hasattr(route, "path"):
                for m in route.methods:
                    if m in ("GET", "POST", "PATCH", "PUT", "DELETE"):
                        actual.add((m, route.path))
        frozen = set(FROZEN_ROUTES)
        missing = frozen - actual
        assert not missing, f"Missing frozen routes: {missing}"


def test_events_generation_pipeline_G1_G2():
    service = EventsService()
    with tempfile.TemporaryDirectory() as tmp:
        app = create_app(service=service, out_dir=tmp)
        client = TestClient(app)

        r = client.post(
            "/venues",
            json={
                "name": "Main Hall",
                "slug": "main-hall",
                "address": "123 Street",
                "capacity": 100,
            },
        )
        assert r.status_code == 200, r.text
        venue_id = r.json()["id"]

        start = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        end = (datetime.now(UTC) + timedelta(days=1, hours=2)).isoformat()

        r = client.post(
            "/events",
            json={
                "title": "Python Meetup",
                "slug": "python-meetup",
                "description": "Community Python meetup with talks and networking session",
                "venue_id": venue_id,
                "start_time": start,
                "end_time": end,
                "capacity": 2,
            },
        )
        assert r.status_code == 200, r.text
        event_id = r.json()["id"]
        assert r.json()["is_published"] is False

        r = client.post(f"/events/{event_id}/publish")
        assert r.status_code == 200
        assert r.json()["is_published"] is True

        r = client.patch(
            f"/events/{event_id}/seo",
            json={
                "seo_title": "Python Meetup SEO",
                "seo_description": "Best meetup",
                "canonical_url": "/events/main-hall/python-meetup/",
            },
        )
        assert r.status_code == 200
        assert r.json()["seo"]["seo_title"] == "Python Meetup SEO"

        r = client.get("/public/events/python-meetup")
        assert r.status_code == 200
        assert r.json()["slug"] == "python-meetup"

        r = client.post(f"/events/{event_id}/rsvp", json={"attendee_name": "Alice"})
        assert r.status_code == 200, r.text
        rsvp_id = r.json()["id"]
        assert r.json()["status"] == "CONFIRMED"

        r = client.post(f"/events/{event_id}/rsvp", json={"attendee_name": "Bob"})
        assert r.status_code == 200

        r = client.post(f"/events/{event_id}/rsvp", json={"attendee_name": "Charlie"})
        assert r.status_code == 400
        assert "FULL" in r.text

        r = client.post("/site/generate")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["generated"] >= 4

        out = Path(tmp)
        assert (out / "index.html").exists()
        assert (out / "events" / "index.html").exists()
        assert (out / "events" / "main-hall" / "index.html").exists()
        assert (out / "events" / "main-hall" / "python-meetup" / "index.html").exists()
        assert (out / "sitemap.xml").exists()

        html = (
            out / "events" / "main-hall" / "python-meetup" / "index.html"
        ).read_text(encoding="utf-8")
        assert "Python Meetup" in html or "python-meetup" in html
        assert (
            "/events/main-hall/python-meetup/" in html
            or "python-meetup" in html.lower()
        )

        r = client.post(f"/rsvps/{rsvp_id}/cancel")
        assert r.status_code == 200
        assert r.json()["status"] == "CANCELLED"

        r = client.post(f"/events/{event_id}/rsvp", json={"attendee_name": "Charlie"})
        assert r.status_code == 200

        r = client.post(f"/events/{event_id}/unpublish")
        assert r.status_code == 200
        r = client.get("/public/events/python-meetup")
        assert r.status_code == 404


def test_second_consumer_uses_same_framework_primitives():
    s = Slug("python-meetup")
    assert str(s) == "python-meetup"
    try:
        Slug("bad/slug")
        assert False
    except ValueError:
        pass

    tmpl_dir = Path("showcases/events/templates")
    renderer = JinjaTemplateRenderer(
        str(tmpl_dir)
        if tmpl_dir.exists()
        else str(Path(__file__).parent.parent / "showcases" / "events" / "templates")
    )
    injector = SeoInjector()
    seo_ctx = SeoContext(
        seo_title="Test",
        seo_description="desc",
        og_title="Test",
        og_description="desc",
        canonical_url="/test/",
        title="Test",
    )
    html = "<html><head></head><body>hi</body></html>"
    injected = injector.ensure_seo(html, seo_ctx)
    assert isinstance(injected, str)

    page = GeneratedPage(
        path="events/main-hall/python-meetup/index.html",
        html="<html>meetup</html>",
        kind="event",
    )
    assert page.path == "events/main-hall/python-meetup/index.html"

    writer = StaticSiteWriter()
    assert hasattr(writer, "write")
    assert callable(getattr(writer, "write"))
