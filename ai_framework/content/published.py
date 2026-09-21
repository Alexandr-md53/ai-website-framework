from __future__ import annotations
from typing import Iterable, TypeVar, List
from .protocols import PublishableProtocol
from .publish_status import PublishStatus

T = TypeVar("T", bound=PublishableProtocol)


def _is_published_status(status) -> bool:
    if isinstance(status, PublishStatus):
        return status.is_published()
    try:
        val = status.value if hasattr(status, "value") else str(status)
        return str(val).lower() == "published"
    except Exception:
        return False


def list_published(items: Iterable[T]) -> List[T]:
    """
    Pure function — no mutation, no IO, no persistence.
    Returns new list with only PUBLISHED items.
    """
    result: List[T] = []
    for i in items:
        if _is_published_status(getattr(i, "status", None)):
            result.append(i)
    return result


def is_published(item: PublishableProtocol) -> bool:
    return _is_published_status(getattr(item, "status", None))
