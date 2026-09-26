from __future__ import annotations
from typing import List
from ai_framework.rendering.generated_page import GeneratedPage
from showcases.events.services.events_renderer import EventsRenderer
from showcases.events.services.events_service import EventsService


class EventsSiteGenerator:
    def __init__(self, service: EventsService, renderer: EventsRenderer):
        self.service = service
        self.renderer = renderer

    def generate(self) -> List[GeneratedPage]:
        pages: List[GeneratedPage] = []
        seen = set()

        def add_page(path: str, html: str, kind: str = "page"):
            if path in seen:
                raise ValueError(f"Duplicate path: {path}")
            seen.add(path)
            pages.append(GeneratedPage(path=path, html=html, kind=kind))

        venues = sorted(self.service.list_venues(), key=lambda v: v.slug)
        events_published = sorted(
            self.service.list_published(), key=lambda e: e.start_time
        )

        add_page(
            "index.html",
            self.renderer.render_index(venues, events_published),
            kind="index",
        )
        add_page(
            "events/index.html",
            self.renderer.render_events_index(venues, events_published),
            kind="events_index",
        )

        for venue in venues:
            venue_events = sorted(
                self.service.list_published(venue_slug=venue.slug),
                key=lambda e: e.start_time,
            )
            add_page(
                f"events/{venue.slug}/index.html",
                self.renderer.render_venue(venue, venue_events),
                kind="venue",
            )
            for ev in venue_events:
                rsvp_count = len(
                    [
                        r
                        for r in self.service.list_rsvps(ev.id)
                        if r.status.value == "CONFIRMED"
                    ]
                )
                html, _ = self.renderer.render_event(ev, venue.slug, rsvp_count)
                add_page(
                    f"events/{venue.slug}/{ev.slug}/index.html", html, kind="event"
                )

        sitemap_content = self.renderer.render_sitemap(pages)
        add_page("sitemap.xml", sitemap_content, kind="sitemap")

        return sorted(pages, key=lambda p: p.path)
