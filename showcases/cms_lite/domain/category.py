from dataclasses import dataclass
import uuid
from typing import Optional
@dataclass
class Category:
    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str] = None
    def validate(self):
        if not self.name.strip() or not self.slug.strip():
            raise ValueError("Category name/slug required")
