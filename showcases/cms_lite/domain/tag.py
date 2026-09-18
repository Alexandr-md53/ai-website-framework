from dataclasses import dataclass
import uuid
@dataclass
class Tag:
    id: uuid.UUID
    name: str
    slug: str
    def validate(self):
        if not self.name.strip():
            raise ValueError("Tag name required")
