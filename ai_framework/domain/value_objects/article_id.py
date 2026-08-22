from dataclasses import dataclass


@dataclass(frozen=True)
class ArticleId:
    value: str
