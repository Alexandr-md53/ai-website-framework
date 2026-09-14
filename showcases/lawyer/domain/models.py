# coding: utf-8, ASCII only
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List
import uuid
from enum import Enum


class ConsultationStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"


@dataclass
class Service:
    id: uuid.UUID
    title: str
    base_fee: Decimal = Decimal("0.00")


@dataclass
class PracticeArea:
    id: uuid.UUID
    title: str
    services: List[Service] = field(default_factory=list)


@dataclass
class Attorney:
    id: uuid.UUID
    name: str
    practice_areas: List[PracticeArea] = field(default_factory=list)


@dataclass
class ConsultationRequest:
    id: uuid.UUID
    client_name: str
    client_email: str
    attorney_id: uuid.UUID
    service_id: uuid.UUID
    status: ConsultationStatus = ConsultationStatus.PENDING
