from dataclasses import dataclass
from typing import Optional
import uuid


@dataclass
class Category:
    id: uuid.UUID
    name: str
    slug: str
    parent_id: Optional[uuid.UUID] = None