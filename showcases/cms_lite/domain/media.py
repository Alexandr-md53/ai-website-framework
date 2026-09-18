from dataclasses import dataclass
import uuid
from typing import Optional
from enum import Enum
class MediaType(str, Enum):
    IMAGE = "IMAGE"
    DOCUMENT = "DOCUMENT"
@dataclass
class Media:
    id: uuid.UUID
    filename: str
    filepath: str
    media_type: MediaType = MediaType.IMAGE
    item_id: Optional[uuid.UUID] = None
    alt_text: Optional[str] = None
