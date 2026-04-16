import httpx
import traceback
from aiogram import types, Router, F
from aiogram.filters import Command
from loguru import logger
from datetime import datetime

from bot.i18n import i18n as t

router = Router()


async def fetch_observer_data(endpoint: str, params: dict = None) -> dict | None:
    """
    Получает данные из Observer API.
    
    Args:
        endpoint: Путь эндпоинта (без префикса /observer)
        params: Query parameters
        
    Returns:
        JSON response или None при ошибке
    """
    try:
        # URL API согласно docker-compose (cfo_api:8002)
        base_url = "http://cfo_api:8002/observer"
        url = f"{base_url}/{endpoint}" if endpoint else base_url
        
        async with httpx.AsyncClient(timeout=30.0) as client:  # timeout 30s как в TASK.md
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Observer API returned {response.status_code}: {response.text}")
                return None
                
    except httpx.ConnectError:
        logger.error("Cannot connect to Observer API")
        return None
    except httpx.Timeout:
        logger.error("Observer API timeout (30s)")
        return None
    except Exception as e:
        logger.error(f"Error fetching observer data: {e}\n{traceback.format_exc()}")
        return None


def format_anomalies_response(data: dict) -> str:
    """
    Форматирует ответ GET /anomalies для Telegram.
    
    Args:
        data: JSON response от API
        
    Returns:
        Отформатированное сообщение
    """
    month_key = data.get("month_key", "unknown")
    anomalies = data.get("anomalies", [])
    detection_status = data.get("detection_status", "ok")
    
    # Определяем статус детекции
    status_text = ""
    if detection_status == "insufficient_history":
        status_text = "⚠️ *Недостаточно истории*: данных за 3 предыдущих месяца нет.\n"
    elif detection_status == "skip_mode":
        status_text = "⏭️ *Режим skip*: месяц без конвертации в USD, аномалии не детектятся.\n"
    
    if not anomalies:
        return (
            f"📊 *Аномалии за {month_key}*\n"
            f"{status_text}"
            f"✅ Аномалий не обнаружено."
        )
    
    # Форматируем список аномалий
    anomalies_text = ""
    for i, anomaly in enumerate(anomalies, 1):
        category = anomaly.get("category", "Unknown")
        current_val = anomaly.get("current_val", 0)
        baseline_val = anomaly.get("baseline_val", 0)
        delta_pct = anomaly.get("delta_pct", 0)
        status = anomaly.get("status", "new")
        detected_at = anomaly.get("detected_at", "")
        
        # Парсим дату для красивого отображения
        detected_time = ""
        if detected_at:
            try:
                dt = datetime.fromisoformat(detected_at.replace('Z', '+00:00'))
                detected_time = dt.strftime("%d.%m %H:%M")
            except:
                detected_time = detected_at
        
        status_emoji = "🆕" if status == "new" else "📨" if status == "notified" else "❌"
        
        anomalies_text += (
            f"{i}. *{category}*\n"
            f"   Текущий: ${current_val:.2f} | Базовый: ${baseline_val:.2f}\n"
            f"   Отклонение: +{delta_pct:.1f}% {status_emoji}\n"
            f"   Обнаружено: {detected_time}\n\n"
        )
    
    return (
        f"📊 *Аномалии за {month_key}*\n"
        f"{status_text}"
        f"Найдено {len(anomalies)} аномалий:\n\n"
        f"{anomalies_text}"
        f"_Статусы: 🆕 new, 📨 notified, ❌ dismissed_"
    )


def format_trends_response(data: dict) -> str:
    """
    Форматирует ответ GET /trends для Telegram.
    
    Args:
        data: JSON response от API
        
    Returns:
        Отформатированное сообщение с таблицей
    """
    period = data.get("period", [])
    metrics = data.get("metrics", [])
    
    if not period:
        return "📈 *Тренды*\nНет данных для отображения."
    
    # Создаём таблицу
    header = "| Месяц | Расходы | Доходы | Сбережения | Burn Rate |\n"
    separator = "|-------|---------|--------|------------|-----------|\n"
    table = header + separator
    
    for metric in metrics:
        month_key = metric.get("month_key", "")
        total_spent = metric.get("total_spent", 0)
        total_income = metric.get("total_income", 0)
        savings_rate = metric.get("savings_rate", 0)  # в процентах
        burn_rate = metric.get("burn_rate", 0)
        rate_type = metric.get("rate_type", "")
        
        # Рассчитываем сбережения в деньгах
        savings_amount = total_income - total_spent
        
        # Форматируем числа
        spent_fmt = f"${total_spent:,.0f}" if total_spent >= 1000 else f"${total_spent:.0f}"
        income_fmt = f"${total_income:,.0f}" if total_income >= 1000 else f"${total_income:.0f}"
        savings_fmt = f"${savings_amount:,.0f}" if abs(savings_amount) >= 1000 else f"${savings_amount:.0f}"
        burn_fmt = f"${burn_rate:,.0f}" if burn_rate >= 1000 else f"${burn_rate:.0f}"
        
        # Эмодзи для rate_type
        rate_emoji = "💱" if rate_type == "manual" else "⏭️" if rate_type == "skip" else "❓"
        
        table += f"| {month_key} {rate_emoji} | {spent_fmt} | {income_fmt} | {savings_fmt} ({savings_rate:.1f}%) | {burn_fmt} |\n"
    
    # Добавляем summary
    if len(metrics) >= 2:
        # Рассчитываем изменения между первым и последним месяцем
        first = metrics[0]
        last = metrics[-1]
        
        spent_change = ((last["total_spent"] - first["total_spent"]) / first["total_spent"] * 100) if first["total_spent"] > 0 else 0
        income_change = ((last["total_income"] - first["total_income"]) / first["total_income"] * 100) if first["total_income"] > 0 else 0
        
        summary = (
            f"\n📈 *Изменения за период:*\n"
            f"• Расходы: {spent_change:+.1f}%\n"
            f"• Доходы: {income_change:+.1f}%\n"
        )
        
        # Проверяем совместимость валют
        has_skip = any(m.get("rate_type") == "skip" for m in metrics)
        if has_skip:
            summary += f"\n⚠️ *Внимание:* В периоде есть месяцы без конвертации (⏭️). Сравнение может быть некорректным."
    else:
        summary = ""
    
    return f"📈 *Тренды за {len(period)} месяцев*\n\n```\n{table}```{summary}"


@router.message(Command("anomalies"))
async def cmd_anomalies(message: types.Message):
    """Обработчик команды /anomalies"""
    try:
        # Парсим параметры команды
        command_text = message.text.strip()
        parts = command_text.split()
        
        params = {}
        if len(parts) > 1:
            # Проверяем формат month_key (YYYY-MM)
            month_param = parts[1]
            if len(month_param) == 7 and month_param[4] == '-':
                params["month_key"] = month_param
            else:
                await message.reply(
                    t("observer.invalid_month_format"),
                    parse_mode="Markdown"
                )
                return
        
        # Отправляем статус обработки
        processing_msg = await message.reply(t("observer.anomalies_search"))
        
        # Получаем данные из API
        data = await fetch_observer_data("anomalies", params)
        
        if data is None:
            await processing_msg.edit_text(t("observer.api_connect_error"))
            return
        
        # Форматируем и отправляем ответ
        formatted = format_anomalies_response(data)
        await processing_msg.edit_text(formatted, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in cmd_anomalies: {e}\n{traceback.format_exc()}")
        await message.reply(t("observer.anomalies_error", error=str(e)), parse_mode="Markdown")


@router.message(Command("trends"))
async def cmd_trends(message: types.Message):
    """Обработчик команды /trends"""
    try:
        # Парсим параметры команды
        command_text = message.text.strip()
        parts = command_text.split()
        
        params = {}
        if len(parts) > 1:
            try:
                months_param = int(parts[1])
                if 1 <= months_param <= 12:
                    params["months"] = months_param
                else:
                    await message.reply(
                        t("observer.invalid_months_range"),
                        parse_mode="Markdown"
                    )
                    return
            except ValueError:
                await message.reply(
                    t("observer.invalid_parameter"),
                    parse_mode="Markdown"
                )
                return
        
        # Отправляем статус обработки
        processing_msg = await message.reply(t("observer.trends_analysis"))
        
        # Получаем данные из API
        data = await fetch_observer_data("trends", params)
        
        if data is None:
            await processing_msg.edit_text(t("observer.api_connect_error"))
            return
        
        # Форматируем и отправляем ответ
        formatted = format_trends_response(data)
        await processing_msg.edit_text(formatted, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in cmd_trends: {e}\n{traceback.format_exc()}")
        await message.reply(t("observer.trends_error", error=str(e)), parse_mode="Markdown")