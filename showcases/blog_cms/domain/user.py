from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
import uuid
from typing import Optional


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"
    GENERATOR = "GENERATOR"  # for static build


class PermissionDeniedError(Exception):
    pass


@dataclass(frozen=True)
class UserContext:
    user_id: str
    role: UserRole


@dataclass(frozen=True)
class PipelineContext:
    """Unified context for Type B pipeline: Domain -> Generator -> Renderer -> Output"""

    user: UserContext
    trace_id: str

    @staticmethod
    def from_raw(
        x_user_id: Optional[str],
        x_user_role: Optional[str],
        trace_id: Optional[str] = None,
    ) -> "PipelineContext":
        # ---- boundary normalization (single place) ----
        uid = x_user_id or "system-generator"
        try:
            uuid.UUID(uid)
            uid_str = uid
        except Exception:
            uid_str = str(uuid.uuid5(uuid.NAMESPACE_DNS, uid))
        role_raw = (x_user_role or "EDITOR").strip().upper()
        try:
            role = UserRole(role_raw)
        except Exception:
            role = UserRole.VIEWER if role_raw == "VIEWER" else UserRole.EDITOR
        if role == UserRole.VIEWER:
            # VIEWER cannot trigger generation, downgrade handled in service guard
            pass
        user = UserContext(user_id=uid_str, role=role)
        return PipelineContext(user=user, trace_id=trace_id or str(uuid.uuid4()))
