from __future__ import annotations
import uuid
import re
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_slug(slug: str) -> None:
    if not SLUG_RE.match(slug):
        raise ValueError(f"Invalid slug: {slug}")


class SeoMeta(BaseModel):
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    canonical_url: Optional[str] = None


class EventStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"


class RsvpStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class Venue(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    address: str = ""
    capacity: Optional[int] = None
    is_published: bool = True


class Event(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    description: str
    venue_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    capacity: Optional[int] = None
    is_published: bool = False
    status: EventStatus = EventStatus.DRAFT
    seo: Optional[SeoMeta] = None

    @property
    def is_upcoming(self) -> bool:
        from datetime import datetime, UTC

        now = datetime.now(UTC)
        # ensure timezone-aware comparison
        st = self.start_time
        if st.tzinfo is None:
            from datetime import timezone

            st = st.replace(tzinfo=timezone.utc)
        return st > now


class Rsvp(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    attendee_name: str
    status: RsvpStatus = RsvpStatus.CONFIRMED
    created_at: str
