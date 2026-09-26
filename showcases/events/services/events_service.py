from __future__ import annotations
import uuid
from typing import Dict, List, Optional
from datetime import datetime, UTC

from showcases.events.domain.models_v01 import (
    Venue,
    Event,
    EventStatus,
    Rsvp,
    RsvpStatus,
    SeoMeta,
    validate_slug,
)


class NotFoundError(Exception):
    pass


class DuplicateSlugError(Exception):
    pass


class ValidationError(Exception):
    pass


class CapacityFullError(Exception):
    pass


class EventsService:
    def __init__(self) -> None:
        self._venues: Dict[uuid.UUID, Venue] = {}
        self._venue_slug_index: Dict[str, uuid.UUID] = {}
        self._events: Dict[uuid.UUID, Event] = {}
        self._event_slug_index: Dict[str, uuid.UUID] = {}
        self._rsvps: Dict[uuid.UUID, Rsvp] = {}

    # ---- Venue ----
    def create_venue(
        self, name: str, slug: str, address: str = "", capacity: Optional[int] = None
    ) -> Venue:
        validate_slug(slug)
        if slug in self._venue_slug_index:
            raise DuplicateSlugError(f"Venue slug duplicate: {slug}")
        if capacity is not None and capacity < 0:
            raise ValidationError("capacity >=0")
        vid = uuid.uuid4()
        venue = Venue(
            id=vid,
            name=name,
            slug=slug,
            address=address,
            capacity=capacity,
            is_published=True,
        )
        self._venues[vid] = venue
        self._venue_slug_index[slug] = vid
        return venue

    def list_venues(self) -> List[Venue]:
        return list(self._venues.values())

    def get_venue(self, venue_id: uuid.UUID) -> Venue:
        if venue_id not in self._venues:
            raise NotFoundError(f"Venue {venue_id} not found")
        return self._venues[venue_id]

    # ---- Event ----
    def create_event(
        self,
        title: str,
        slug: str,
        description: str,
        venue_id: uuid.UUID,
        start_time: datetime,
        end_time: datetime,
        capacity: Optional[int] = None,
    ) -> Event:
        validate_slug(slug)
        if slug in self._event_slug_index:
            raise DuplicateSlugError(f"Event slug duplicate: {slug}")
        if venue_id not in self._venues:
            raise NotFoundError(f"Venue {venue_id} not found")
        if len(description.strip()) < 10:
            raise ValidationError("description >=10")
        if start_time >= end_time:
            raise ValidationError("start_time must be < end_time")
        if capacity is not None and capacity < 0:
            raise ValidationError("capacity >=0")
        # ensure UTC
        if start_time.tzinfo is None or end_time.tzinfo is None:
            raise ValidationError("start_time/end_time must be timezone-aware UTC")
        eid = uuid.uuid4()
        ev = Event(
            id=eid,
            title=title,
            slug=slug,
            description=description,
            venue_id=venue_id,
            start_time=start_time,
            end_time=end_time,
            capacity=capacity,
            is_published=False,
            status=EventStatus.DRAFT,
        )
        self._events[eid] = ev
        self._event_slug_index[slug] = eid
        return ev

    def get_event(self, event_id: uuid.UUID) -> Event:
        if event_id not in self._events:
            raise NotFoundError(f"Event {event_id} not found")
        return self._events[event_id]

    def list_events(self) -> List[Event]:
        return list(self._events.values())

    def list_published(
        self, venue_slug: Optional[str] = None, upcoming_only: bool = False
    ) -> List[Event]:
        events = [
            e
            for e in self._events.values()
            if e.is_published and e.status == EventStatus.PUBLISHED
        ]
        if venue_slug:
            vid = self._venue_slug_index.get(venue_slug)
            if not vid:
                return []
            events = [e for e in events if e.venue_id == vid]
        if upcoming_only:
            now = datetime.now(UTC)
            events = [e for e in events if e.start_time > now]
        return sorted(events, key=lambda x: x.start_time)

    def get_published_by_slug(self, slug: str) -> Event:
        eid = self._event_slug_index.get(slug)
        if not eid:
            raise NotFoundError(f"Slug {slug} not found")
        ev = self._events[eid]
        if not ev.is_published or ev.status != EventStatus.PUBLISHED:
            raise NotFoundError(f"Event {slug} not published")
        return ev

    def update_event(
        self,
        event_id: uuid.UUID,
        title: Optional[str] = None,
        description: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        capacity: Optional[int] = None,
    ) -> Event:
        ev = self.get_event(event_id)
        if title is not None:
            if len(title.strip()) < 2:
                raise ValidationError("title >=2")
            ev.title = title
        if description is not None:
            if len(description.strip()) < 10:
                raise ValidationError("description >=10")
            ev.description = description
        if start_time is not None:
            if start_time.tzinfo is None:
                raise ValidationError("start_time must be timezone-aware")
            ev.start_time = start_time
        if end_time is not None:
            if end_time.tzinfo is None:
                raise ValidationError("end_time must be timezone-aware")
            ev.end_time = end_time
        if ev.start_time >= ev.end_time:
            raise ValidationError("start_time < end_time")
        if capacity is not None:
            if capacity < 0:
                raise ValidationError("capacity >=0")
            ev.capacity = capacity
        return ev

    def update_seo(
        self,
        event_id: uuid.UUID,
        seo_title: Optional[str],
        seo_description: Optional[str],
        canonical_url: Optional[str],
    ) -> Event:
        ev = self.get_event(event_id)
        ev.seo = SeoMeta(
            seo_title=seo_title,
            seo_description=seo_description,
            canonical_url=canonical_url,
        )
        return ev

    def publish(self, event_id: uuid.UUID) -> Event:
        ev = self.get_event(event_id)
        if len(ev.description.strip()) < 10:
            raise ValidationError("Cannot publish: description <10")
        if ev.start_time >= ev.end_time:
            raise ValidationError("Cannot publish: invalid time range")
        ev.is_published = True
        ev.status = EventStatus.PUBLISHED
        return ev

    def unpublish(self, event_id: uuid.UUID) -> Event:
        ev = self.get_event(event_id)
        ev.is_published = False
        ev.status = EventStatus.DRAFT
        return ev

    def cancel(self, event_id: uuid.UUID) -> Event:
        ev = self.get_event(event_id)
        ev.is_published = False
        ev.status = EventStatus.CANCELLED
        return ev

    # ---- RSVP ----
    def _confirmed_count(self, event_id: uuid.UUID) -> int:
        return len(
            [
                r
                for r in self._rsvps.values()
                if r.event_id == event_id and r.status == RsvpStatus.CONFIRMED
            ]
        )

    def create_rsvp(self, event_id: uuid.UUID, attendee_name: str) -> Rsvp:
        ev = self.get_event(event_id)
        if not ev.is_published or ev.status != EventStatus.PUBLISHED:
            raise ValidationError(f"Event {ev.slug} not published")
        if not attendee_name or len(attendee_name.strip()) < 2:
            raise ValidationError("attendee_name >=2")
        # capacity check — showcase-local, NOT generic CapacityManager
        if ev.capacity is not None:
            confirmed = self._confirmed_count(event_id)
            if confirmed >= ev.capacity:
                raise CapacityFullError(
                    f"Event {ev.slug} FULL: capacity {ev.capacity} reached"
                )
        rid = uuid.uuid4()
        rsvp = Rsvp(
            id=rid,
            event_id=event_id,
            attendee_name=attendee_name.strip(),
            status=RsvpStatus.CONFIRMED,
            created_at=datetime.now(UTC).isoformat(),
        )
        self._rsvps[rid] = rsvp
        return rsvp

    def get_rsvp(self, rsvp_id: uuid.UUID) -> Rsvp:
        if rsvp_id not in self._rsvps:
            raise NotFoundError(f"Rsvp {rsvp_id} not found")
        return self._rsvps[rsvp_id]

    def list_rsvps(self, event_id: Optional[uuid.UUID] = None) -> List[Rsvp]:
        if event_id:
            return [r for r in self._rsvps.values() if r.event_id == event_id]
        return list(self._rsvps.values())

    def cancel_rsvp(self, rsvp_id: uuid.UUID) -> Rsvp:
        rsvp = self.get_rsvp(rsvp_id)
        if rsvp.status == RsvpStatus.CANCELLED:
            return rsvp
        rsvp.status = RsvpStatus.CANCELLED
        return rsvp
