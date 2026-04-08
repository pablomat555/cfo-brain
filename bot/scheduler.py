"""
APScheduler для еженедельного дайджеста CFO Brain.

Контракт D-20: Scheduler живёт в боте, вызывает только API endpoints.
"""
import asyncio
import httpx
from datetime import datetime
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot


async def weekly_digest(bot: Bot, chat_id: int):
    """
    Формирует и отправляет еженедельный дайджест.
    
    Вызывает:
    - GET /trends?months=3 (тренды за 3 месяца)
    - GET /anomalies (последний полный месяц, статус new)
    """
    api_base = "http://cfo_api:8002/observer"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Получаем тренды
            trends_response = await client.get(
                f"{api_base}/trends",
                params={"months": 3}
            )
            
            if trends_response.status_code != 200:
                logger.error(f"Failed to fetch trends: {trends_response.status_code}")
                trends_data = None
            else:
                trends_data = trends_response.json()
            
            # 2. Получаем аномалии за последний полный месяц
            anomalies_response = await client.get(
                f"{api_base}/anomalies",
                params={"status": "new"}
            )
            
            if anomalies_response.status_code != 200:
                logger.error(f"Failed to fetch anomalies: {anomalies_response.status_code}")
                anomalies_data = None
            else:
                anomalies_data = anomalies_response.json()
            
            # 3. Форматируем сообщение
            lines = ["📊 *Еженедельный дайджест CFO Brain*", ""]
            
            # Тренды
            if trends_data and trends_data.get("metrics"):
                metrics = trends_data["metrics"]
                lines.append("*Тренды за 3 месяца:*")
                for item in metrics:
                    month = item["month_key"]
                    burn = item["burn_rate"]
                    save = item["savings_rate"] * 100  # в процентах
                    spent = item["total_spent"]
                    income = item["total_income"]
                    
                    lines.append(
                        f"  {month}: burn={burn:.1f}, save={save:.1f}%, "
                        f"spent=${spent:.0f}, income=${income:.0f}"
                    )
            else:
                lines.append("*Тренды:* данных недостаточно")
            
            lines.append("")
            
            # Аномалии
            if anomalies_data:
                detection_status = anomalies_data.get("detection_status")
                anomalies = anomalies_data.get("anomalies", [])
                month_key = anomalies_data.get("month_key", "N/A")
                
                if detection_status == "ok" and anomalies:
                    lines.append(f"*Аномалии за {month_key}:*")
                    for i, anomaly in enumerate(anomalies[:5]):  # топ-5
                        lines.append(
                            f"  {i+1}. {anomaly['category']}: "
                            f"{anomaly['delta_pct']:.1f}% "
                            f"({anomaly['current_val']:.0f} vs {anomaly['baseline_val']:.0f})"
                        )
                    if len(anomalies) > 5:
                        lines.append(f"  ... и ещё {len(anomalies) - 5}")
                elif detection_status == "pending":
                    lines.append(f"*Аномалии за {month_key}:* обработка ещё не завершена")
                elif detection_status == "insufficient_history":
                    lines.append(f"*Аномалии за {month_key}:* недостаточно истории (<3 месяцев)")
                elif detection_status == "skip_mode":
                    lines.append(f"*Аномалии за {month_key}:* режим skip (конвертация отключена)")
                else:
                    lines.append(f"*Аномалии за {month_key}:* аномалий не обнаружено")
            else:
                lines.append("*Аномалии:* не удалось получить данные")
            
            lines.append("")
            lines.append("_Дайджест сформирован автоматически._")
            
            message_text = "\n".join(lines)
            
            # 4. Отправляем в Telegram
            await bot.send_message(
                chat_id,
                message_text,
                parse_mode="Markdown"
            )
            logger.info(f"Weekly digest sent to chat {chat_id}")
            
    except Exception as e:
        logger.error(f"Error in weekly_digest: {e}")
        # Не падаем, просто логируем


def setup_scheduler(bot: Bot, chat_id: int) -> AsyncIOScheduler:
    """
    Создаёт и настраивает scheduler с еженедельным job.
    
    Время: каждый понедельник в 09:00 по Europe/Kyiv.
    """
    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    
    # Добавляем job
    scheduler.add_job(
        weekly_digest,
        trigger=CronTrigger(day_of_week="mon", hour=9, minute=0),
        args=[bot, chat_id],
        id="weekly_digest",
        replace_existing=True,
        misfire_grace_time=3600  # допуск 1 час
    )
    
    logger.info(f"Scheduler configured for chat {chat_id} (Monday 09:00 Europe/Kyiv)")
    return scheduler