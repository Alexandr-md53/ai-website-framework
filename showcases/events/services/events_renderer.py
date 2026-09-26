from __future__ import annotations
from pathlib import Path
from typing import List
from ai_framework.rendering.jinja import JinjaTemplateRenderer
from ai_framework.rendering.generated_page import GeneratedPage
from ai_framework.rendering.seo import SeoContext, SeoInjector


class EventsRenderer:
    def __init__(self, templates_dir: Path | None = None):
        if templates_dir is None:
            candidates = [
                Path(__file__).parent.parent / "templates",
                Path(__file__).parent / "templates",
                Path("showcases/events/templates"),
            ]
            for c in candidates:
                if c.exists():
                    templates_dir = c
                    break
            if templates_dir is None:
                templates_dir = candidates[0]
        self.templates_dir = Path(templates_dir)
        self.renderer = JinjaTemplateRenderer(str(self.templates_dir))
        self.seo_injector = SeoInjector()

    def _make_seo(
        self,
        seo_title: str,
        seo_description: str = "",
        canonical_url: str = "",
        title_fallback: str = "",
    ) -> SeoContext:
        return SeoContext(
            seo_title=seo_title,
            seo_description=seo_description,
            og_title=seo_title,
            og_description=seo_description,
            canonical_url=canonical_url,
            title=title_fallback or seo_title,
        )

    def _seo_for_event(self, event, page_url: str) -> SeoContext:
        seo_title = (
            event.seo.seo_title if event.seo and event.seo.seo_title else event.title
        )
        seo_desc = (
            event.seo.seo_description
            if event.seo and event.seo.seo_description
            else event.description[:160]
        )
        canonical = (
            event.seo.canonical_url
            if event.seo and event.seo.canonical_url
            else page_url
        )
        return self._make_seo(seo_title, seo_desc, canonical, event.title)

    def render_event(self, event, venue_slug: str, rsvp_count: int = 0):
        page_url = f"/events/{venue_slug}/{event.slug}/"
        seo_ctx = self._seo_for_event(event, page_url)
        html = self.renderer.render(
            "event.html",
            {
                "event": event,
                "venue_slug": venue_slug,
                "page_url": page_url,
                "rsvp_count": rsvp_count,
                "start_time": event.start_time.isoformat(),
                "end_time": event.end_time.isoformat(),
                "is_upcoming": event.start_time.isoformat(),
            },
        )
        try:
            html = self.seo_injector.ensure_seo(html, seo_ctx)
        except Exception:
            pass
        return html, seo_ctx

    def render_venue(self, venue, events: List) -> str:
        page_url = f"/events/{venue.slug}/"
        seo_ctx = self._make_seo(
            f"{venue.name} — Events", f"Events at {venue.name}", page_url, venue.name
        )
        html = self.renderer.render(
            "venue.html",
            {"venue": venue, "events": events, "page_url": page_url},
        )
        try:
            html = self.seo_injector.ensure_seo(html, seo_ctx)
        except Exception:
            pass
        return html

    def render_events_index(self, venues, events) -> str:
        page_url = "/events/"
        seo_ctx = self._make_seo(
            "Events — Community", "All upcoming events", page_url, "Events"
        )
        html = self.renderer.render(
            "events_index.html",
            {"venues": venues, "events": events, "page_url": page_url},
        )
        try:
            html = self.seo_injector.ensure_seo(html, seo_ctx)
        except Exception:
            pass
        return html

    def render_index(self, venues, events) -> str:
        page_url = "/"
        seo_ctx = self._make_seo(
            "Events — Home", "Community events home", page_url, "Events"
        )
        html = self.renderer.render(
            "index.html",
            {"venues": venues, "events": events, "page_url": page_url},
        )
        try:
            html = self.seo_injector.ensure_seo(html, seo_ctx)
        except Exception:
            pass
        return html

    def render_sitemap(self, pages: List[GeneratedPage]) -> str:
        urls = [p.path for p in pages if not p.path.endswith("sitemap.xml")]
        xml_parts = []
        xml_parts.append('<?xml version="1.0" encoding="UTF-8"?>')
        xml_parts.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
        for u in sorted(urls):
            loc = f"/{u}" if not u.startswith("/") else u
            if loc.endswith("index.html"):
                loc = loc[:-10] or "/"
            xml_parts.append(f"  <url><loc>{loc}</loc></url>")
        xml_parts.append("</urlset>")
        return "\n".join(xml_parts)
