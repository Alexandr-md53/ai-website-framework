from __future__ import annotations
from typing import Protocol
from .publish_status import PublishStatus
from .slug import Slug


class PublishableProtocol(Protocol):
    """
    Narrow publish lifecycle protocol — only status + slug.
    No id, title, to_dict, content, seo, taxonomy.
    """

    @property
    def status(self) -> PublishStatus: ...

    @property
    def slug(self) -> Slug | str: ...
