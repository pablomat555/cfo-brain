"""
verdict.py — Telegram handler для команды /verdict.

Только форматирование. Никакой логики (D-28).
Язык: русский (единый стандарт бота).

Команда: /verdict <amount> <category> [expense_type]

Примеры:
    /verdict 500 стоматология exceptional
    /verdict 1500 инвестиции strategic
    /verdict 200 продукты
"""

import httpx
import traceback
from aiogram import types, Router, F
from aiogram.filters import Command
from loguru import logger

router = Router()

# ─────────────────────────────────────────────
# Строки (константы)
# ─────────────────────────────────────────────

MSG_VERDICT_HEADER = "💡 Вердикт: {decision}"
MSG_CATEGORY = "📋 Категория: {category} ({expense_type})"
MSG_AMOUNT = "💵 Сумма: ${amount}"
MSG_LIQUIDITY_BEFORE = "📊 Ликвидность до: ~${value}"
MSG_LIQUIDITY_AFTER = "📊 Ликвидность после: ~${value}"
MSG_IMPACT = "⚠️ Impact: {level} ({pct}%)"
MSG_LIQUIDITY_WARNING_YES = "🔔 Предупреждение о ликвидности: да"
MSG_LIQUIDITY_WARNING_NO = "🔔 Предупреждение о ликвидности: нет"
MSG_SNAPSHOT_DATE = "📅 Capital snapshot: {date}"
MSG_CAPITAL_STATE_EMPTY = "⚠️ Capital State не загружен. Используй /capital_add."
MSG_ERROR = "❌ Ошибка: {error}"
MSG_USAGE = (
    "Использование: /verdict <сумма> <категория> [тип расхода]\n\n"
    "Примеры:\n"
    "/verdict 500 стоматология exceptional\n"
    "/verdict 1500 инвестиции strategic\n"
    "/verdict 200 продукты"
)

# API URL
_API_URL = "http://cfo_api:8002/verdict"


@router.message(Command("verdict"))
async def cmd_verdict(message: types.Message):
    """Обработчик команды /verdict."""
    try:
        # Парсим аргументы
        parts = message.text.strip().split()
        if len(parts) < 3:
            await message.reply(MSG_USAGE, parse_mode="Markdown")
            return

        amount_str = parts[1]
        category = parts[2]
        expense_type = parts[3] if len(parts) > 3 else "routine"

        # Валидируем сумму
        try:
            amount = float(amount_str)
        except ValueError:
            await message.reply("❌ Неверная сумма. Введите число.", parse_mode="Markdown")
            return

        # Вызываем API
        verdict_data = await _call_api(amount, category, expense_type)

        if verdict_data is None:
            await message.reply(MSG_CAPITAL_STATE_EMPTY, parse_mode="Markdown")
            return

        # Форматируем ответ
        reply_text = _format_verdict(verdict_data, amount, category, expense_type)
        await message.reply(reply_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in cmd_verdict: {e}\n{traceback.format_exc()}")
        await message.reply(MSG_ERROR.format(error=str(e)), parse_mode="Markdown")


async def _call_api(amount: float, category: str, expense_type: str) -> dict | None:
    """Вызвать API вердикта."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                _API_URL,
                json={
                    "amount": amount,
                    "currency": "USD",
                    "category": category,
                    "expense_type": expense_type,
                }
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 400:
                # Capital state пустой
                return None
            else:
                logger.error(f"API returned {response.status_code}: {response.text}")
                return None

    except httpx.ConnectError:
        logger.error("Cannot connect to API")
        return None
    except Exception as e:
        logger.error(f"Error calling API: {e}\n{traceback.format_exc()}")
        return None


def _format_verdict(data: dict, amount: float, category: str, expense_type: str) -> str:
    """Форматировать ответ вердикта."""
    decision = data.get("decision", "UNKNOWN")
    impact_level = data.get("impact_level", "UNKNOWN")
    capital_after = data.get("capital_after", 0)
    liquidity_warning = data.get("liquidity_warning", False)
    meta = data.get("meta", {})
    liquid_before = meta.get("liquid_before", 0)
    last_updated = meta.get("last_updated", "N/A")

    # Форматируем решение
    decision_display = decision.replace("_", " ")

    # Форматируем числа
    amount_formatted = f"{amount:,.0f}" if amount == int(amount) else f"{amount:,.2f}"
    liquid_before_formatted = f"{liquid_before:,.0f}" if liquid_before == int(liquid_before) else f"{liquid_before:,.2f}"
    capital_after_formatted = f"{capital_after:,.0f}" if capital_after == int(capital_after) else f"{capital_after:,.2f}"

    # Impact percentage
    if liquid_before > 0:
        impact_pct = (amount / liquid_before) * 100
        impact_pct_formatted = f"{impact_pct:.1f}"
    else:
        impact_pct_formatted = "N/A"

    # Форматируем дату snapshot
    snapshot_date_formatted = _format_date(last_updated)

    # Собираем ответ
    lines = [
        MSG_VERDICT_HEADER.format(decision=decision_display),
        "",
        MSG_CATEGORY.format(category=category, expense_type=expense_type),
        MSG_AMOUNT.format(amount=amount_formatted),
        "",
        MSG_LIQUIDITY_BEFORE.format(value=liquid_before_formatted),
        MSG_LIQUIDITY_AFTER.format(value=capital_after_formatted),
        MSG_IMPACT.format(level=impact_level, pct=impact_pct_formatted),
        MSG_LIQUIDITY_WARNING_YES if liquidity_warning else MSG_LIQUIDITY_WARNING_NO,
        "",
        MSG_SNAPSHOT_DATE.format(date=snapshot_date_formatted),
    ]

    return "\n".join(lines)


def _format_date(date_str: str) -> str:
    """Форматировать дату в читаемый формат."""
    if not date_str:
        return "N/A"

    try:
        from datetime import datetime
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        months = {
            1: "янв", 2: "фев", 3: "мар", 4: "апр", 5: "май", 6: "июн",
            7: "июл", 8: "авг", 9: "сен", 10: "окт", 11: "ноя", 12: "дек"
        }
        return f"{dt.day} {months.get(dt.month, '?')} {dt.year}"
    except Exception:
        return date_str
