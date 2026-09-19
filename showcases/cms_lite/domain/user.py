from dataclasses import dataclass
import uuid
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"

@dataclass
class User:
    id: uuid.UUID
    email: str
    role: UserRole = UserRole.EDITOR
    is_active: bool = True
    def validate(self):
        if "@" not in self.email:
            raise ValueError("validation.invalid_email:email")

@dataclass
class UserContext:
    user_id: str
    role: UserRole

class PermissionDeniedError(Exception):
    pass
