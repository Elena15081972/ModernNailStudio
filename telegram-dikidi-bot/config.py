"""Конфигурация бота из переменных окружения (.env)."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Не задана переменная окружения {name}. Скопируйте .env.example в .env и заполните его."
        )
    return value


class Config:
    telegram_token: str = _required("TELEGRAM_BOT_TOKEN")

    # "mock" — работать на встроенной имитации DIKIDI (для разработки и теста бота
    #           без доступа к реальному API);
    # "live" — ходить в настоящий DIKIDI API.
    dikidi_mode: str = os.getenv("DIKIDI_MODE", "mock").lower()

    dikidi_base_url: str = os.getenv("DIKIDI_API_BASE_URL", "https://api.dikidi.ru/v1")
    dikidi_company_id: str = os.getenv("DIKIDI_COMPANY_ID", "")
    dikidi_api_key: str = os.getenv("DIKIDI_API_KEY", "")
    dikidi_timezone: str = os.getenv("DIKIDI_TIMEZONE", "Europe/Moscow")

    storage_path: str = os.getenv("BOT_STORAGE_PATH", "./bot_storage.sqlite3")

    def validate_live(self) -> None:
        if self.dikidi_mode != "live":
            return
        missing = [
            name
            for name, value in (
                ("DIKIDI_COMPANY_ID", self.dikidi_company_id),
                ("DIKIDI_API_KEY", self.dikidi_api_key),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                "DIKIDI_MODE=live, но не заполнены переменные: " + ", ".join(missing)
            )


config = Config()
