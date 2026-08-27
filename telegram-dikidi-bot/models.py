"""Общие структуры данных, которыми обмениваются nlp.py, dikidi_client.py и bot.py."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class Service:
    id: int
    name: str
    duration_min: int = 0
    price: float | None = None


@dataclass
class Staff:
    id: int
    name: str


@dataclass
class TimeSlot:
    """Одно свободное окошко: время + мастер, который в это время свободен."""

    time: str  # "14:00"
    staff_id: int
    staff_name: str


@dataclass
class ParsedRequest:
    """Результат разбора сообщения клиента на естественном языке."""

    day: date | None
    explicit_time: str | None  # "14:00", если клиент указал время явно
    client_name: str | None
    raw_text: str


@dataclass
class PendingBooking:
    """Состояние диалога записи, которое живёт в context.chat_data между шагами."""

    day: date
    service: Service
    client_name: str
    slots: list[TimeSlot]
    chosen_slot: TimeSlot | None = None
    phone: str | None = None
