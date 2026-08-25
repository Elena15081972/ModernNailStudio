"""Тесты разбора свободного текста: дата, время-подсказка, имя клиента, услуга.

Используем фиксированный now=..., чтобы тесты не зависели от текущей даты
запуска (иначе "завтра"/"в пятницу" были бы каждый день разными).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import nlp
from models import Service

NOW = datetime(2026, 3, 10, 12, 0)  # вторник

SERVICES = [
    Service(id=1, name="Стрижка", duration_min=60, price=2500),
    Service(id=2, name="Маникюр", duration_min=90, price=3000),
    Service(id=3, name="Окрашивание", duration_min=150, price=6500),
]


def test_extract_date_tomorrow():
    assert nlp.extract_date("завтра", now=NOW) == (NOW + timedelta(days=1)).date()


def test_extract_date_day_after_tomorrow():
    assert nlp.extract_date("послезавтра", now=NOW) == (NOW + timedelta(days=2)).date()


def test_extract_date_today_inside_sentence():
    assert nlp.extract_date("хочу записаться сегодня вечером на стрижку", now=NOW) == NOW.date()


def test_extract_date_weekday_in_sentence():
    result = nlp.extract_date("хочу записаться в пятницу на маникюр", now=NOW)
    assert result == date(2026, 3, 13)  # ближайшая пятница после вторника 10.03


def test_extract_date_numeric_dd_mm():
    result = nlp.extract_date("запиши на 27.08 на окрашивание, Мария", now=NOW)
    assert result == date(2026, 8, 27)


def test_extract_date_full_booking_sentence():
    text = "Запиши меня на завтра на стрижку в 14:00, Елена"
    assert nlp.extract_date(text, now=NOW) == (NOW + timedelta(days=1)).date()


def test_extract_date_returns_none_without_any_date_hint():
    assert nlp.extract_date("хочу подстричься покороче", now=NOW) is None


def test_extract_explicit_time_found():
    text = "Запиши меня на завтра на стрижку в 14:00, Елена"
    assert nlp.extract_explicit_time(text) == "14:00"


def test_extract_explicit_time_not_confused_by_numeric_date():
    assert nlp.extract_explicit_time("запиши на 27.08 на окрашивание") is None


def test_extract_explicit_time_absent():
    assert nlp.extract_explicit_time("хочу записаться в пятницу на маникюр") is None


def test_extract_client_name_after_comma():
    text = "Запиши меня на завтра на стрижку в 14:00, Елена"
    assert nlp.extract_client_name(text) == "Елена"


def test_extract_client_name_capitalized_fallback():
    text = "запиши на 27.08 на окрашивание, Мария"
    assert nlp.extract_client_name(text) == "Мария"


def test_extract_client_name_absent():
    assert nlp.extract_client_name("хочу записаться в пятницу на маникюр") is None


def test_extract_service_exact_match():
    text = "Запиши меня на завтра на стрижку в 14:00, Елена"
    service = nlp.extract_service(text, SERVICES)
    assert service is not None
    assert service.name == "Стрижка"


def test_extract_service_fuzzy_typo():
    service = nlp.extract_service("хочу записатся на маникюр завтра", SERVICES)
    assert service is not None
    assert service.name == "Маникюр"


def test_extract_service_not_found():
    assert nlp.extract_service("хочу записаться завтра", SERVICES) is None


def test_parse_booking_request_combines_all_fields():
    text = "Запиши меня на завтра на стрижку в 14:00, Елена"
    parsed = nlp.parse_booking_request(text, now=NOW)
    assert parsed.day == (NOW + timedelta(days=1)).date()
    assert parsed.explicit_time == "14:00"
    assert parsed.client_name == "Елена"
    assert parsed.raw_text == text
