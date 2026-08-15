import pytest
from unittest.mock import AsyncMock, MagicMock
from ai_framework.crud.slug_orchestrator import AsyncSlugOrchestrator


@pytest.fixture
def mock_slug_generator():
    generator = MagicMock()
    generator.generate.side_effect = lambda text: text.lower().strip().replace(" ", "-")
    return generator


@pytest.fixture
def mock_collision_resolver():
    resolver = MagicMock()
    resolver.max_attempts = 5
    resolver.format_candidate.side_effect = lambda base, attempt: f"{base}-{attempt}"
    return resolver


@pytest.fixture
def mock_persistence():
    provider = MagicMock()
    provider.is_unique = AsyncMock(return_value=True)
    return provider


@pytest.fixture
def orchestrator(mock_slug_generator, mock_collision_resolver, mock_persistence):
    return AsyncSlugOrchestrator(
        slug_generator=mock_slug_generator,
        collision_resolver=mock_collision_resolver,
        persistence_provider=mock_persistence,
    )


@pytest.mark.asyncio
async def test_process_generates_new_slug(orchestrator, mock_persistence):
    payload = {"title": "Test Article"}
    result = await orchestrator.process("article", payload)

    assert result["slug"] == "test-article"
    assert result is not payload  # Убеждаемся, что исходный словарь не мутировал
    mock_persistence.is_unique.assert_called_once_with(
        "article", "slug", "test-article"
    )


@pytest.mark.asyncio
async def test_process_preserves_existing_slug(orchestrator, mock_persistence):
    payload = {"title": "Test Article", "slug": "custom-slug"}
    result = await orchestrator.process("article", payload)

    assert result["slug"] == "custom-slug"
    mock_persistence.is_unique.assert_not_called()


@pytest.mark.asyncio
async def test_process_resolves_collisions(orchestrator, mock_persistence):
    # Первый вызов — коллизия (False), второй — уникальный (True)
    mock_persistence.is_unique = AsyncMock(side_effect=[False, True])

    payload = {"title": "Test Article"}
    result = await orchestrator.process("article", payload)

    assert result["slug"] == "test-article-2"
    assert mock_persistence.is_unique.call_count == 2


@pytest.mark.asyncio
async def test_process_exceeds_max_attempts_raises_error(
    orchestrator, mock_persistence
):
    # Постоянная коллизия
    mock_persistence.is_unique = AsyncMock(return_value=False)

    payload = {"title": "Test Article"}
    with pytest.raises(RuntimeError, match="Could not resolve unique slug"):
        await orchestrator.process("article", payload)


@pytest.mark.asyncio
async def test_process_custom_source_and_target_fields(orchestrator, mock_persistence):
    payload = {"headline": "Breaking News"}
    result = await orchestrator.process(
        "news",
        payload,
        source_field="headline",
        target_field="permalink",
    )

    assert result["permalink"] == "breaking-news"
    mock_persistence.is_unique.assert_called_once_with(
        "news", "permalink", "breaking-news"
    )


@pytest.mark.asyncio
async def test_process_missing_source_returns_original_payload(
    orchestrator, mock_persistence
):
    payload = {"content": "No title or headline"}
    result = await orchestrator.process("article", payload)

    assert result == payload
    mock_persistence.is_unique.assert_not_called()
