"""Клиент DIKIDI Business API.

ВАЖНО ПРО ЭНДПОИНТЫ
--------------------
DIKIDI не публикует открытую REST-документацию — партнёрский API-ключ и точный
контракт (пути запросов, формат ответа) выдаются индивидуально после того, как
вы напишете в поддержку DIKIDI / своему аккаунт-менеджеру и опишете сценарий
использования (см. README.md, раздел «Доступ к DIKIDI API»).

Пути в словаре ENDPOINTS ниже — это типовой REST-контракт (такой же формы,
как у большинства их партнёрских интеграций). Когда DIKIDI пришлёт вам точную
спецификацию — поправьте пути и, если нужно, поля в *_from_json() ниже. Больше
нигде в проекте эндпоинты не хардкодятся, весь код bot.py работает через
методы этого класса.
"""

from __future__ import annotations

import logging
import random
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta

import requests

from models import Service, Staff, TimeSlot

logger = logging.getLogger(__name__)

ENDPOINTS = {
    "services": "/services",
    "staff": "/staff",
    "free_times": "/records/free_times",
    "clients_search": "/clients",
    "clients_create": "/clients",
    "records_create": "/records",
}


class DikidiAPIError(RuntimeError):
    """Ошибка запроса к DIKIDI (сетевая, HTTP или бизнес-ошибка в ответе)."""


class DikidiClient(ABC):
    """Интерфейс, которым пользуется bot.py — не зависит от того, реальный это API или мок."""

    @abstractmethod
    def list_services(self) -> list[Service]: ...

    @abstractmethod
    def list_staff(self, service_id: int) -> list[Staff]: ...

    @abstractmethod
    def get_free_slots(self, day: date, service_id: int, staff_id: int) -> list[TimeSlot]:
        """Свободные времена конкретного мастера на конкретную услугу в этот день."""

    @abstractmethod
    def find_or_create_client(self, full_name: str, phone: str) -> int:
        """Возвращает id клиента в DIKIDI, создавая его при первом обращении."""

    @abstractmethod
    def create_appointment(
        self, day: date, time: str, service_id: int, staff_id: int, client_id: int
    ) -> str:
        """Создаёт запись в журнале. Возвращает человекочитаемое подтверждение."""


class LiveDikidiClient(DikidiClient):
    """Реальные HTTP-вызовы к DIKIDI Business API."""

    def __init__(self, base_url: str, company_id: str, api_key: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.company_id = company_id
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            }
        )

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}{path}"
        try:
            response = self._session.request(method, url, timeout=self.timeout, **kwargs)
        except requests.RequestException as exc:
            raise DikidiAPIError(f"Не удалось связаться с DIKIDI ({method} {path}): {exc}") from exc

        if response.status_code >= 400:
            raise DikidiAPIError(
                f"DIKIDI API вернул ошибку {response.status_code} на {method} {path}: {response.text[:500]}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise DikidiAPIError(f"DIKIDI API вернул не-JSON ответ на {method} {path}") from exc

        if isinstance(payload, dict) and payload.get("success") is False:
            raise DikidiAPIError(payload.get("message", "Неизвестная ошибка DIKIDI API"))

        return payload

    def list_services(self) -> list[Service]:
        payload = self._request(
            "GET", ENDPOINTS["services"], params={"company_id": self.company_id}
        )
        return [
            Service(
                id=row["id"],
                name=row.get("title") or row.get("name", ""),
                duration_min=row.get("duration", 0),
                price=row.get("price"),
            )
            for row in payload.get("data", [])
        ]

    def list_staff(self, service_id: int) -> list[Staff]:
        payload = self._request(
            "GET",
            ENDPOINTS["staff"],
            params={"company_id": self.company_id, "service_id": service_id},
        )
        return [Staff(id=row["id"], name=row.get("name", "")) for row in payload.get("data", [])]

    def get_free_slots(self, day: date, service_id: int, staff_id: int) -> list[TimeSlot]:
        payload = self._request(
            "GET",
            ENDPOINTS["free_times"],
            params={
                "company_id": self.company_id,
                "service_id": service_id,
                "staff_id": staff_id,
                "date": day.isoformat(),
            },
        )
        staff_name = ""
        slots = []
        for row in payload.get("data", []):
            staff_name = row.get("staff_name", staff_name)
            slots.append(TimeSlot(time=row["time"], staff_id=staff_id, staff_name=staff_name))
        return slots

    def find_or_create_client(self, full_name: str, phone: str) -> int:
        found = self._request(
            "GET",
            ENDPOINTS["clients_search"],
            params={"company_id": self.company_id, "phone": phone},
        )
        existing = found.get("data") or []
        if existing:
            return existing[0]["id"]

        created = self._request(
            "POST",
            ENDPOINTS["clients_create"],
            json={"company_id": self.company_id, "name": full_name, "phone": phone},
        )
        return created["data"]["id"]

    def create_appointment(
        self, day: date, time: str, service_id: int, staff_id: int, client_id: int
    ) -> str:
        self._request(
            "POST",
            ENDPOINTS["records_create"],
            json={
                "company_id": self.company_id,
                "date": day.isoformat(),
                "time": time,
                "service_id": service_id,
                "staff_id": staff_id,
                "client_id": client_id,
            },
        )
        return f"Запись создана на {day.strftime('%d.%m.%Y')} в {time}."


class MockDikidiClient(DikidiClient):
    """Имитация DIKIDI для разработки и проверки диалога бота без реального API-ключа.

    Держит услуги/мастеров/записи в памяти процесса. Свободные слоты — с 09:00 до
    19:00 каждые 30 минут минус несколько случайно "занятых" на каждый день, чтобы
    было видно, что список окошек меняется.
    """

    def __init__(self) -> None:
        self._services = [
            Service(id=1, name="Маникюр", duration_min=30, price=900),
            Service(id=2, name="Маникюр с покрытием лаком", duration_min=60, price=1000),
            Service(id=3, name="Маникюр с покрытием гель-лак", duration_min=60, price=1900),
            Service(id=4, name="Маникюр мужской", duration_min=30, price=1000),
            Service(id=5, name="Снятие гель-лака", duration_min=15, price=300),
            Service(id=6, name="Наращивание ногтей", duration_min=90, price=2500),
            Service(id=7, name="Педикюр + обычный лак", duration_min=95, price=1600),
            Service(id=8, name="Педикюр полностью (+стопы)", duration_min=120, price=1900),
            Service(id=9, name="Педикюр (пальчики) + гель-лак", duration_min=60, price=1700),
            Service(id=10, name="Педикюр + гель-лак", duration_min=75, price=2400),
            Service(id=11, name="Маникюр + педикюр с гель-лаком", duration_min=120, price=3700),
        ]
        self._staff = [
            Staff(id=101, name="Евгения"),
            Staff(id=102, name="Гуля"),
        ]
        self._booked: set[tuple[date, str, int]] = set()
        self._clients: dict[str, int] = {}
        self._next_client_id = 1000

    def list_services(self) -> list[Service]:
        return list(self._services)

    def list_staff(self, service_id: int) -> list[Staff]:
        return list(self._staff)

    def get_free_slots(self, day: date, service_id: int, staff_id: int) -> list[TimeSlot]:
        staff = next((s for s in self._staff if s.id == staff_id), None)
        if staff is None:
            return []

        rng = random.Random(f"{day}-{staff_id}")
        slots: list[TimeSlot] = []
        cur = datetime.combine(day, datetime.min.time()).replace(hour=9, minute=0)
        end = cur.replace(hour=19, minute=0)
        while cur < end:
            time_str = cur.strftime("%H:%M")
            if (day, time_str, staff_id) not in self._booked and rng.random() > 0.25:
                slots.append(TimeSlot(time=time_str, staff_id=staff_id, staff_name=staff.name))
            cur += timedelta(minutes=30)
        return slots

    def find_or_create_client(self, full_name: str, phone: str) -> int:
        if phone in self._clients:
            return self._clients[phone]
        self._next_client_id += 1
        self._clients[phone] = self._next_client_id
        logger.info("MOCK: создан клиент %s (%s) -> id=%s", full_name, phone, self._next_client_id)
        return self._next_client_id

    def create_appointment(
        self, day: date, time: str, service_id: int, staff_id: int, client_id: int
    ) -> str:
        self._booked.add((day, time, staff_id))
        logger.info(
            "MOCK: запись создана day=%s time=%s service=%s staff=%s client=%s",
            day,
            time,
            service_id,
            staff_id,
            client_id,
        )
        return f"Запись создана на {day.strftime('%d.%m.%Y')} в {time}."


def build_client(cfg) -> DikidiClient:
    if cfg.dikidi_mode == "live":
        cfg.validate_live()
        return LiveDikidiClient(
            base_url=cfg.dikidi_base_url,
            company_id=cfg.dikidi_company_id,
            api_key=cfg.dikidi_api_key,
        )
    logger.warning(
        "DIKIDI_MODE=%s — бот работает на встроенной имитации DIKIDI, реальные записи не создаются.",
        cfg.dikidi_mode,
    )
    return MockDikidiClient()
