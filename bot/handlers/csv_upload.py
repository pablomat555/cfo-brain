import asyncio
import httpx
from aiogram import types, Router, F, Bot
from aiogram.fsm.context import FSMContext
from loguru import logger

from core.config import get_settings

async def poll_for_anomalies(month_key: str, chat_id: int, bot: Bot):
    """
    Bounded polling для проверки завершения scan.
    
    Контракт D-23: 3 попытки, интервал 2с, стоп на detection_status != "pending".
    Если есть аномалии — отправляет alert, иначе молча завершается.
    """
    api_url = "http://cfo_api:8002/observer/anomalies"
    
    for attempt in range(3):
        await asyncio.sleep(2.0)  # интервал 2 секунды
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    api_url,
                    params={"month_key": month_key, "status": "new"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    detection_status = data.get("detection_status")
                    
                    if detection_status != "pending":
                        anomalies = data.get("anomalies", [])
                        if anomalies:
                            # Формируем alert
                            alert_lines = [
                                "🚨 Обнаружены аномалии после загрузки CSV:",
                                f"Месяц: {month_key}",
                                f"Найдено аномалий: {len(anomalies)}",
                                "",
                                "Топ аномалий по отклонению:"
                            ]
                            
                            for i, anomaly in enumerate(anomalies[:3]):  # показываем топ-3
                                alert_lines.append(
                                    f"{i+1}. {anomaly['category']}: "
                                    f"{anomaly['delta_pct']:.1f}% "
                                    f"({anomaly['current_val']:.0f} vs {anomaly['baseline_val']:.0f})"
                                )
                            
                            if len(anomalies) > 3:
                                alert_lines.append(f"... и ещё {len(anomalies) - 3}")
                            
                            alert_text = "\n".join(alert_lines)
                            await bot.send_message(chat_id, alert_text)
                        # Если аномалий нет — молчим
                        return
        except Exception as e:
            logger.warning(f"Polling attempt {attempt + 1} failed: {e}")
    
    logger.info(f"Polling completed for month_key={month_key}, detection_status may still be pending")


router = Router()


@router.message(F.document, F.document.file_name.endswith(".csv"))
async def handle_csv_upload(message: types.Message, bot: Bot, state: FSMContext):
    """Обработчик загрузки CSV файлов"""
    document = message.document
    
    await message.reply("⏳ Обрабатываю файл...")
    
    try:
        # Скачиваем файл
        file = await bot.get_file(document.file_id)
        file_bytes = await bot.download_file(file.file_path)
        
        # Отправляем в API
        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {"file": (document.file_name, file_bytes, "text/csv")}
            response = await client.post(
                "http://cfo_api:8002/ingest/csv",
                files=files
            )
            
            if response.status_code == 200:
                result = response.json()
                inserted = result.get("inserted", 0)
                skipped = result.get("skipped_duplicates", 0)
                skipped_technical = result.get("skipped_technical", 0)  # НОВОЕ
                errors = result.get("errors", 0)
                
                reply_text = (
                    f"✅ Загружено: {inserted} транзакций.\n"
                    f"📋 Дублей пропущено: {skipped}.\n"
                    f"⚙️ Технических записей пропущено: {skipped_technical}.\n"
                    f"⚠️ Ошибок: {errors}."
                )
                
                if errors > 0:
                    reply_text += "\n\nНекоторые строки не удалось обработать. Проверьте логи."
                
                # Запускаем bounded polling для последнего полного месяца
                # Определяем month_key как последний полный месяц (как в observer)
                # Для простоты используем текущий месяц минус один месяц
                from datetime import date
                from dateutil.relativedelta import relativedelta
                last_month = date.today().replace(day=1) - relativedelta(months=1)
                month_key = last_month.strftime("%Y-%m")
                
                # Запускаем polling асинхронно, не блокируя ответ
                asyncio.create_task(
                    poll_for_anomalies(month_key, message.chat.id, bot)
                )
                logger.info(f"Started polling for month_key={month_key} after CSV upload")
                    
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                reply_text = "❌ Ошибка обработки файла. Попробуй ещё раз."
        
        await message.reply(reply_text)
        
    except httpx.ConnectError:
        logger.error("Cannot connect to CFO API")
        await message.reply("❌ Не могу подключиться к API. Убедитесь, что сервис запущен.")
    except Exception as e:
        logger.error(f"Error processing CSV: {e}")
        await message.reply("❌ Ошибка обработки файла. Попробуй ещё раз.")