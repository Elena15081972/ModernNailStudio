"""Свободные ответы клиенту (приветствие, цена, возражения) через OpenAI по prompt.md.

Вызывается только пока клиент не назвал одновременно услугу и день — как только
это происходит, дальше ведёт детерминированный сценарий в bot.py (реальная
проверка расписания DIKIDI и кнопки), а не эта LLM.
"""

from __future__ import annotations

from pathlib import Path

from openai import OpenAI

from config import config

_PROMPT_PATH = Path(__file__).parent / "prompt.md"
_client = OpenAI(api_key=config.openai_api_key)


def _system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def draft_reply(client_message: str) -> str:
    response = _client.chat.completions.create(
        model=config.openai_model,
        messages=[
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": client_message},
        ],
        max_tokens=400,
    )
    return response.choices[0].message.content or "Не удалось сформировать ответ, уточните вопрос ещё раз."
