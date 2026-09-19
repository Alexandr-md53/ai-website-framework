from dataclasses import dataclass
import uuid
@dataclass
class Tag:
    id: uuid.UUID
    name: str
    slug: str
    def validate(self):
        if not self.name or not self.name.strip():
            raise ValueError("validation.required:name")
        if not self.slug or not self.slug.strip():
            raise ValueError("validation.required:slug")
