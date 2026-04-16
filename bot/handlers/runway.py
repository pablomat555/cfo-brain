"""
runway.py — Telegram handler для команды /runway.

Только форматирование. Никакой логики (D-28).
Язык: русский (единый стандарт бота).

Команда: /runway
"""

import httpx
import traceback
from aiogram import types, Router, F
from aiogram.filters import Command
from loguru import logger

from bot.i18n import i18n as t

router = Router()

# API URL
_API_URL = "http://cfo_api:8002/runway"


@router.message(Command("runway"))
async def cmd_runway(message: types.Message):
    """Обработчик команды /runway."""
    try:
        # Вызываем API
        runway_data = await _call_api()

        if runway_data is None:
            await message.reply(t("runway.no_data"), parse_mode="Markdown")
            return

        # Форматируем ответ
        reply_text = _format_runway(runway_data)
        await message.reply(reply_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in cmd_runway: {e}\n{traceback.format_exc()}")
        await message.reply(t("runway.error", error=str(e)), parse_mode="Markdown")


async def _call_api() -> dict | None:
    """Вызвать API runway."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(_API_URL)
            if response.status_code == 400:
                # Нет данных или capital state пустой
                return None
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            return None
        logger.error(f"HTTP error in runway API: {e}")
        raise
    except Exception as e:
        logger.error(f"Network error in runway API: {e}")
        raise


def _format_runway(data: dict) -> str:
    """Форматировать ответ runway в читаемый текст."""
    lines = [t("runway.header"), ""]

    # Основные метрики
    lines.append(t("runway.capital",
        capital_snapshot=data["capital_snapshot"],
        as_of=data["as_of"][:10]  # YYYY-MM-DD
    ))
    lines.append(t("runway.burn",
        burn_rate_avg=data["burn_rate_avg"],
        months_used=data["scenario"]["months_history"]
    ))
    lines.append(t("runway.income", income_avg=data["income_avg"]))

    # Delta (положительный/отрицательный)
    monthly_delta = data["monthly_delta"]
    if monthly_delta >= 0:
        lines.append(t("runway.delta_positive", monthly_delta=monthly_delta))
    else:
        lines.append(t("runway.delta_negative", monthly_delta_abs=abs(monthly_delta)))

    lines.append("")

    # Статус
    if data["runway_status"] == "self_sustaining":
        lines.append(t("runway.self_sustaining"))
    else:
        # depleting
        if data["runway_months"] is not None:
            lines.append(t("runway.depleting_header",
                emergency_floor=data["emergency_floor"],
                runway_months=data["runway_months"]
            ))
        if data["runway_months_liquid_zero"] is not None:
            lines.append(t("runway.depleting_zero",
                runway_months_liquid_zero=data["runway_months_liquid_zero"]
            ))

    lines.append("")

    # Дополнительная информация
    lines.append(t("runway.trend", burn_trend=data["burn_trend"]))
    lines.append(t("runway.emergency_floor", emergency_floor=data["emergency_floor"]))

    # Предупреждение
    if data.get("warning"):
        lines.append("")
        lines.append(t("runway.warning", warning=data["warning"]))

    return "\n".join(lines)