"""Publications service: business rules on top of the SQL store.

Stage 2 only: no HTTP, no scheduler, no admin UI, no web wiring of the feature
flag.  ``publications_enabled()`` is the single service-side check of
``VIDEOSHOP_PUBLICATIONS`` (default off; anything but ``on`` means off).
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from ..domain.catalog import ValidationError, validate_language
from ..domain.publications import (
    DEFAULT_TIMEZONE,
    SUPPORTED_PLATFORMS,
    Channel,
    Publication,
    PublicationJob,
    PublicationText,
    PublishResult,
    validate_channel_key,
    validate_credentials_ref,
    validate_timezone,
)
from ..infrastructure.publications_store import PublicationsStore


def _validate_iso_moment(value: str, *, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValidationError(f"{field_name} is required")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValidationError(f"{field_name} must carry a timezone offset")
    return text


class PublicationsService:
    """Validated entry point for every publications operation."""

    def __init__(
        self, provider: Any, *, now: Optional[Callable[[], str]] = None
    ) -> None:
        self._store = PublicationsStore(provider, now=now)

    # ------------------------------------------------------------ feature flag
    def publications_enabled(self) -> bool:
        return os.getenv("VIDEOSHOP_PUBLICATIONS", "off").strip().lower() == "on"

    # ---------------------------------------------------------------- channels
    def create_channel(
        self,
        *,
        channel_key: Any,
        name: Any,
        credentials_ref: Any,
        platform: str = "telegram",
        settings_json: str = "{}",
        default_language: str = "",
        timezone: str = DEFAULT_TIMEZONE,
        is_active: bool = True,
    ) -> Channel:
        if platform not in SUPPORTED_PLATFORMS:
            raise ValidationError(
                f"platform must be one of {list(SUPPORTED_PLATFORMS)}, got {platform!r}"
            )
        key = validate_channel_key(channel_key)
        ref = validate_credentials_ref(credentials_ref)
        zone = validate_timezone(timezone)
        title = str(name or "").strip()
        if not title:
            raise ValidationError("channel name is required")
        language = str(default_language or "").strip()
        if language:
            validate_language(language)
        return self._store.insert_channel(
            platform=platform,
            channel_key=key,
            name=title,
            credentials_ref=ref,
            settings_json=settings_json,
            default_language=language,
            timezone=zone,
            is_active=is_active,
        )

    def update_channel(self, channel_id: int, **fields: Any) -> Channel:
        if "channel_key" in fields:
            fields["channel_key"] = validate_channel_key(fields["channel_key"])
        if "credentials_ref" in fields:
            fields["credentials_ref"] = validate_credentials_ref(
                fields["credentials_ref"]
            )
        if "timezone" in fields:
            fields["timezone"] = validate_timezone(fields["timezone"])
        if "default_language" in fields:
            language = str(fields["default_language"] or "").strip()
            if language:
                validate_language(language)
            fields["default_language"] = language
        if "name" in fields:
            title = str(fields["name"] or "").strip()
            if not title:
                raise ValidationError("channel name is required")
            fields["name"] = title
        return self._store.update_channel(channel_id, **fields)

    def set_channel_active(self, channel_id: int, active: bool) -> Channel:
        return self._store.set_channel_active(channel_id, active)

    def list_channels(self, *, active_only: bool = False) -> List[Channel]:
        return self._store.list_channels(active_only=active_only)

    def get_channel(self, channel_id: int) -> Channel:
        return self._store.get_channel(channel_id)

    # ------------------------------------------------------------ publications
    def create_publication(
        self,
        *,
        texts: Mapping[str, Tuple[str, str]],
        kind: str = "manual",
        source_type: str = "",
        source_slug: str = "",
        created_by: str = "",
    ) -> Publication:
        if not texts:
            raise ValidationError("a publication needs at least one language")
        normalized: Dict[str, Tuple[str, str]] = {}
        for lang, pair in texts.items():
            code = validate_language(lang)
            title = str((pair or ("", ""))[0] or "").strip()
            body = str((pair or ("", ""))[1] or "")
            if not title:
                raise ValidationError(f"title for language {code!r} is required")
            normalized[code] = (title, body)
        return self._store.create_publication(
            kind=kind,
            source_type=source_type,
            source_slug=source_slug,
            texts=normalized,
            created_by=str(created_by or ""),
        )

    def get_publication(self, publication_id: int) -> Publication:
        return self._store.get_publication(publication_id)

    def get_texts(self, publication_id: int) -> Dict[str, PublicationText]:
        return self._store.get_texts(publication_id)

    def schedule_jobs(
        self,
        publication_id: int,
        *,
        channel_ids: Sequence[int],
        langs: Sequence[str],
        scheduled_for: str,
    ) -> List[PublicationJob]:
        channels = [int(value) for value in channel_ids]
        if not channels:
            raise ValidationError("at least one channel is required")
        languages: List[str] = []
        for lang in langs:
            code = validate_language(lang)
            if code not in languages:
                languages.append(code)
        if not languages:
            raise ValidationError("at least one language is required")
        moment = _validate_iso_moment(scheduled_for, field_name="scheduled_for")
        return self._store.schedule_jobs(
            publication_id,
            channel_ids=channels,
            langs=languages,
            scheduled_for=moment,
        )

    # ------------------------------------------------------------------- queue
    def claim_due(self, limit: int = 20) -> List[PublicationJob]:
        return self._store.claim_due(limit=limit)

    def finish(
        self, job_id: int, result: PublishResult, *, uncertain: bool = False
    ) -> PublicationJob:
        return self._store.finish(job_id, result, uncertain=uncertain)

    def expire_stale_sends(self, ttl_seconds: int = 600) -> int:
        return self._store.expire_stale_sends(ttl_seconds=ttl_seconds)

    def resolve_uncertain(
        self,
        job_id: int,
        *,
        outcome: str,
        external_id: Optional[str] = None,
        note: str = "",
    ) -> PublicationJob:
        return self._store.resolve_uncertain(
            job_id, outcome=outcome, external_id=external_id, note=note
        )

    def retry_as_new(
        self, job_id: int, *, scheduled_for: Optional[str] = None
    ) -> PublicationJob:
        if scheduled_for is not None:
            scheduled_for = _validate_iso_moment(
                scheduled_for, field_name="scheduled_for"
            )
        return self._store.retry_as_new(job_id, scheduled_for=scheduled_for)

    def list_jobs(
        self,
        publication_id: Optional[int] = None,
        channel_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[PublicationJob]:
        return self._store.list_jobs(
            publication_id=publication_id,
            channel_id=channel_id,
            status=status,
            limit=limit,
        )

    def list_events(self, job_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        return self._store.list_events(job_id, limit=limit)

    def retention_sweep(self) -> int:
        return self._store.retention_sweep()
