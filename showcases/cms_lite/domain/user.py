from dataclasses import dataclass
import uuid
from enum import Enum
class UserRole(str, Enum):
    ADMIN = "ADMIN"
    EDITOR = "EDITOR"
@dataclass
class User:
    id: uuid.UUID
    email: str
    role: UserRole = UserRole.EDITOR
    is_active: bool = True
    def validate(self):
        if "@" not in self.email:
            raise ValueError("Invalid email")
