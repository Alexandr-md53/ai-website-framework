from dataclasses import dataclass
from enum import Enum
from typing import Optional
import uuid


class LightRequirement(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    DIRECT_SUN = "DIRECT_SUN"


class WateringRequirement(str, Enum):
    SPARSE = "SPARSE"
    MODERATE = "MODERATE"
    FREQUENT = "FREQUENT"


@dataclass
class Plant:
    id: uuid.UUID
    category_id: uuid.UUID
    name: str
    description: Optional[str] = None
    light_req: LightRequirement = LightRequirement.MEDIUM
    water_req: WateringRequirement = WateringRequirement.MODERATE
    frost_resistance: int = 0
    main_image_id: Optional[str] = None
