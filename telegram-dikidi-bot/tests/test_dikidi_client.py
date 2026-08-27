"""Тесты MockDikidiClient — проверяют контракт, которым пользуется bot.py,
без обращения к реальному DIKIDI API."""

from __future__ import annotations

from datetime import date, datetime

from dikidi_client import MockDikidiClient

DAY = date(2026, 3, 12)


def test_list_services_returns_known_services():
    client = MockDikidiClient()
    names = {s.name for s in client.list_services()}
    assert "Маникюр" in names
    assert "Педикюр полностью (+стопы)" in names


def test_list_staff_returns_staff():
    client = MockDikidiClient()
    services = client.list_services()
    staff = client.list_staff(services[0].id)
    assert len(staff) >= 1
    assert all(s.name for s in staff)


def test_free_slots_are_within_business_hours_and_half_hour_step():
    client = MockDikidiClient()
    service = client.list_services()[0]
    staff = client.list_staff(service.id)[0]

    slots = client.get_free_slots(DAY, service.id, staff.id)

    assert slots, "мок должен вернуть хотя бы одно свободное окошко"
    for slot in slots:
        hour, minute = map(int, slot.time.split(":"))
        assert 9 <= hour < 19
        assert minute in (0, 30)
        assert slot.staff_id == staff.id
        assert slot.staff_name == staff.name


def test_free_slots_deterministic_for_same_day_and_staff():
    client = MockDikidiClient()
    service = client.list_services()[0]
    staff = client.list_staff(service.id)[0]

    first = client.get_free_slots(DAY, service.id, staff.id)
    second = client.get_free_slots(DAY, service.id, staff.id)

    assert [s.time for s in first] == [s.time for s in second]


def test_free_slots_differ_between_staff():
    client = MockDikidiClient()
    service = client.list_services()[0]
    staff_list = client.list_staff(service.id)
    assert len(staff_list) >= 2

    slots_a = {s.time for s in client.get_free_slots(DAY, service.id, staff_list[0].id)}
    slots_b = {s.time for s in client.get_free_slots(DAY, service.id, staff_list[1].id)}
    assert slots_a != slots_b


def test_create_appointment_removes_slot_from_future_free_slots():
    client = MockDikidiClient()
    service = client.list_services()[0]
    staff = client.list_staff(service.id)[0]

    slots_before = client.get_free_slots(DAY, service.id, staff.id)
    booked_time = slots_before[0].time

    client_id = client.find_or_create_client("Елена", "+79991234567")
    result = client.create_appointment(DAY, booked_time, service.id, staff.id, client_id)
    assert booked_time in result

    slots_after = client.get_free_slots(DAY, service.id, staff.id)
    assert booked_time not in {s.time for s in slots_after}


def test_find_or_create_client_returns_same_id_for_same_phone():
    client = MockDikidiClient()
    first_id = client.find_or_create_client("Елена", "+79991234567")
    second_id = client.find_or_create_client("Елена Смирнова", "+79991234567")
    assert first_id == second_id


def test_find_or_create_client_returns_different_id_for_different_phone():
    client = MockDikidiClient()
    id_a = client.find_or_create_client("Елена", "+79991234567")
    id_b = client.find_or_create_client("Мария", "+79997654321")
    assert id_a != id_b
