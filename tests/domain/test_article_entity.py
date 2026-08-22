import pytest

from ai_framework.domain.entities.article import Article, ArticleStatus
from ai_framework.domain.value_objects.article_id import ArticleId
from ai_framework.domain.value_objects.title import Title
from ai_framework.domain.value_objects.content import Content
from ai_framework.domain.exceptions import (
    DomainValidationError,
    InvalidStateTransitionError,
)


def test_article_initial_state_is_draft():
    article = Article(
        id=ArticleId("123e4567-e89b-12d3-a456-426614174000"),
        title=Title("Clean Architecture in Python"),
        content=Content("Domain-driven design principles..."),
    )
    assert article.status == ArticleStatus.DRAFT


def test_article_publish_success():
    article = Article(
        id=ArticleId("123e4567-e89b-12d3-a456-426614174000"),
        title=Title("Clean Architecture in Python"),
        content=Content("Domain-driven design principles..."),
    )
    article.publish()
    assert article.status == ArticleStatus.PUBLISHED


def test_article_cannot_archive_directly_from_draft():
    article = Article(
        id=ArticleId("123e4567-e89b-12d3-a456-426614174000"),
        title=Title("Clean Architecture in Python"),
        content=Content("Domain-driven design principles..."),
    )
    with pytest.raises(InvalidStateTransitionError):
        article.archive()


def test_article_publish_fails_with_empty_title():
    article = Article(
        id=ArticleId("123e4567-e89b-12d3-a456-426614174000"),
        title=Title(""),
        content=Content("Valid content body..."),
    )
    with pytest.raises(DomainValidationError):
        article.publish()


def test_article_publish_fails_with_empty_content():
    article = Article(
        id=ArticleId("123e4567-e89b-12d3-a456-426614174000"),
        title=Title("Valid Title"),
        content=Content(""),
    )
    with pytest.raises(DomainValidationError):
        article.publish()


def test_article_archive_success_from_published():
    article = Article(
        id=ArticleId("123e4567-e89b-12d3-a456-426614174000"),
        title=Title("Clean Architecture in Python"),
        content=Content("Domain-driven design principles..."),
    )
    article.publish()
    article.archive()
    assert article.status == ArticleStatus.ARCHIVED


def test_article_cannot_update_title_when_published():
    article = Article(
        id=ArticleId("123e4567-e89b-12d3-a456-426614174000"),
        title=Title("Original Title"),
        content=Content("Original Content"),
    )
    article.publish()
    with pytest.raises(DomainValidationError):
        article.update_title(Title("New Title"))


def test_article_update_content_success_in_draft():
    article = Article(
        id=ArticleId("123e4567-e89b-12d3-a456-426614174000"),
        title=Title("Original Title"),
        content=Content("Original Content"),
    )
    article.update_content(Content("Updated Content"))
    assert article.content.value == "Updated Content"
