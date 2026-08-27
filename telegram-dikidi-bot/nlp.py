"""Разбор свободного текста клиента: дата, время (если указано явно), имя, услуга.

Финальное время всегда выбирается клиентом через кнопку (см. bot.py) — время,
найденное здесь, используется только чтобы отсортировать/подсветить подходящие
слоты, а не для автоматической записи.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from difflib import get_close_matches

import dateparser
from dateparser.search import search_dates

from models import ParsedRequest, Service

_TIME_RE = re.compile(r"(?<!\d)([01]?\d|2[0-3])[:.\-\s]([0-5]\d)(?!\d)")
_NUMERIC_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?(?!\d)")
_CLOCK_FRAGMENT_RE = re.compile(r"^(?:в|к)?\s*\d{1,2}[:.]\d{2}$", re.IGNORECASE)

# Частые слова-триггеры, которые не должны попадать в "имя клиента".
_STOPWORDS = {
    "запиши", "меня", "нас", "запись", "хочу", "можно", "пожалуйста",
    "на", "в", "к", "у", "и", "завтра", "сегодня", "послезавтра",
}


def extract_date(text: str, *, now: datetime | None = None) -> date | None:
    """Ищет дату внутри произвольного текста.

    dateparser.parse() умеет разбирать строку, только если она ЦЕЛИКОМ является
    датой — на предложении вроде «Запиши меня на завтра на стрижку в 14:00»
    он молча возвращает None. Поэтому сначала пробуем явный числовой формат
    (27.08, 27.08.2026), а затем — dateparser.search.search_dates(), которая
    ищет дату-подстроку внутри произвольного текста и понимает «завтра»,
    «послезавтра», «в пятницу» и т.п. по-русски.
    """
    now = now or datetime.now()
    settings = {
        "TIMEZONE": "Europe/Moscow",
        "RETURN_AS_TIMEZONE_AWARE": False,
        "PREFER_DATES_FROM": "future",
        "RELATIVE_BASE": now,
    }

    numeric_match = _NUMERIC_DATE_RE.search(text)
    if numeric_match:
        parsed = dateparser.parse(numeric_match.group(0), languages=["ru"], settings=settings)
        if parsed is not None:
            return parsed.date()

    matches = search_dates(text, languages=["ru"], settings=settings) or []
    for fragment, parsed_dt in matches:
        if _CLOCK_FRAGMENT_RE.match(fragment.strip()):
            continue
        return parsed_dt.date()

    return None


def extract_explicit_time(text: str) -> str | None:
    match = _TIME_RE.search(text)
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def extract_client_name(text: str) -> str | None:
    """Эвристика: имя часто идёт последним словом через запятую («...в 14:00, Елена»)
    или как капитализированное слово, которого нет среди стоп-слов."""
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if len(parts) > 1:
        candidate = parts[-1]
        words = candidate.split()
        if len(words) == 1 and words[0].istitle():
            return words[0]

    for word in re.findall(r"[А-ЯЁ][а-яё]+", text):
        if word.lower() not in _STOPWORDS:
            return word

    return None


def extract_service(text: str, services: list[Service]) -> Service | None:
    text_lower = text.lower()

    for service in services:
        if service.name.lower() in text_lower:
            return service

    tokens = re.findall(r"[а-яёa-z]+", text_lower)
    service_names_lower = [s.name.lower() for s in services]
    for token in tokens:
        matches = get_close_matches(token, service_names_lower, n=1, cutoff=0.8)
        if matches:
            idx = service_names_lower.index(matches[0])
            return services[idx]

    return None


def parse_booking_request(text: str, *, now: datetime | None = None) -> ParsedRequest:
    return ParsedRequest(
        day=extract_date(text, now=now),
        explicit_time=extract_explicit_time(text),
        client_name=extract_client_name(text),
        raw_text=text,
    )
