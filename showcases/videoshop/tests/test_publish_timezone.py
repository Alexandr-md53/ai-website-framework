"""S5.1: publish_timezone setting and DST-safe local-to-UTC conversion."""
from __future__ import annotations

from datetime import datetime

import pytest

from showcases.videoshop.domain.catalog import ValidationError, resolve_publish_moment
from showcases.videoshop.infrastructure.image_store import ImageStore
from showcases.videoshop.infrastructure.migrations.catalog import migrate_catalog
from showcases.videoshop.infrastructure.slug_registry import SlugRegistry
from showcases.videoshop.infrastructure.sqlite_provider import VideoShopSQLiteProvider
from showcases.videoshop.services.catalog import CatalogService
from showcases.videoshop.services.publications import PublicationsService

START = "2026-01-01T10:00:00+00:00"


def _catalog(tmp_path):
    provider = VideoShopSQLiteProvider(db_path=str(tmp_path / "shop.sqlite"))
    migrate_catalog(provider)
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    service = CatalogService(provider, SlugRegistry(provider), ImageStore(images_dir))
    return provider, service


def test_publish_timezone_default_chisinau(tmp_path):
    _, catalog = _catalog(tmp_path)
    assert catalog.get_settings().publish_timezone == "Europe/Chisinau"


def test_publish_timezone_persisted_and_validated(tmp_path):
    provider, catalog = _catalog(tmp_path)
    catalog.update_settings({"publish_timezone": "Europe/Bucharest"})
    assert catalog.get_settings().publish_timezone == "Europe/Bucharest"
    with provider.read_transaction() as tx:
        value = tx.scalar(
            "SELECT value FROM shop_settings WHERE key = 'publish_timezone'"
        )
    assert value == "Europe/Bucharest"


def test_publish_timezone_invalid_rejected(tmp_path):
    _, catalog = _catalog(tmp_path)
    with pytest.raises(ValidationError):
        catalog.update_settings({"publish_timezone": "Mars/Base"})
    assert catalog.get_settings().publish_timezone == "Europe/Chisinau"


def test_publish_timezone_change_does_not_touch_existing_jobs(tmp_path):
    provider, catalog = _catalog(tmp_path)
    publications = PublicationsService(provider)
    channel = publications.create_channel(
        channel_key="main",
        name="Main",
        credentials_ref="MAIN",
        settings_json='{"chat_id": "123456789"}',
    )
    publication = publications.create_publication(
        texts={"ru": ("Title", "Body")}, created_by="owner"
    )
    jobs = publications.schedule_jobs(
        publication.id,
        channel_ids=[channel.id],
        langs=["ru"],
        scheduled_for=START,
    )
    assert jobs[0].scheduled_for == START

    catalog.update_settings({"publish_timezone": "Europe/Bucharest"})

    stored = publications.list_jobs(publication_id=publication.id)[0]
    assert stored.scheduled_for == START


def test_dst_spring_forward_2026_03_29():
    assert resolve_publish_moment(
        datetime(2026, 3, 29, 3, 30), "Europe/Chisinau"
    ) == "2026-03-29T01:30:00+00:00"


def test_dst_fall_back_2026_10_25_ambiguous_rejected():
    with pytest.raises(ValidationError) as error:
        resolve_publish_moment(datetime(2026, 10, 25, 3, 30), "Europe/Chisinau")
    assert "ambiguous" in str(error.value)


def test_dst_normal_time_no_shift():
    assert resolve_publish_moment(
        datetime(2026, 6, 15, 12, 0), "Europe/Chisinau"
    ) == "2026-06-15T09:00:00+00:00"
    assert resolve_publish_moment(
        datetime(2026, 3, 29, 2, 30), "Europe/Chisinau"
    ) == "2026-03-29T00:30:00+00:00"
