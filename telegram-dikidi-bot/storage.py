"""Простое хранилище телефонов клиентов, чтобы не спрашивать контакт при каждой записи."""

from __future__ import annotations

import sqlite3
from contextlib import closing


class PhoneStorage:
    def __init__(self, path: str):
        self._path = path
        with closing(sqlite3.connect(self._path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS known_clients (
                    telegram_user_id INTEGER PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    phone TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def get_phone(self, telegram_user_id: int) -> str | None:
        with closing(sqlite3.connect(self._path)) as conn:
            row = conn.execute(
                "SELECT phone FROM known_clients WHERE telegram_user_id = ?",
                (telegram_user_id,),
            ).fetchone()
        return row[0] if row else None

    def save_phone(self, telegram_user_id: int, full_name: str, phone: str) -> None:
        with closing(sqlite3.connect(self._path)) as conn:
            conn.execute(
                """
                INSERT INTO known_clients (telegram_user_id, full_name, phone)
                VALUES (?, ?, ?)
                ON CONFLICT(telegram_user_id) DO UPDATE SET
                    full_name = excluded.full_name,
                    phone = excluded.phone
                """,
                (telegram_user_id, full_name, phone),
            )
            conn.commit()
