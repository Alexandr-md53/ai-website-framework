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
        if not self.name or not self.name.strip():
            raise ValueError("validation.required:name")
        if not self.slug or not self.slug.strip():
            raise ValueError("validation.required:slug")
