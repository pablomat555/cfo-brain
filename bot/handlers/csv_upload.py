import asyncio
import httpx
from aiogram import types, Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from loguru import logger

from core.config import get_settings


class CSVUploadState(StatesGroup):
    """Состояния FSM для загрузки CSV"""
    waiting_for_fx_rate = State()
    file_ready = State()

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


async def _process_csv_with_fx_rate(file_bytes: bytes, filename: str, fx_rate: float, rate_type: str, chat_id: int, bot: Bot) -> str:
    """Вспомогательная функция для обработки CSV с указанным курсом"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {"file": (filename, file_bytes, "text/csv")}
            response = await client.post(
                "http://cfo_api:8002/ingest/csv",
                files=files,
                params={"fx_rate": fx_rate, "rate_type": rate_type}
            )
            
            if response.status_code == 200:
                result = response.json()
                inserted = result.get("inserted", 0)
                skipped = result.get("skipped_duplicates", 0)
                skipped_technical = result.get("skipped_technical", 0)
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
                from datetime import date
                from dateutil.relativedelta import relativedelta
                last_month = date.today().replace(day=1) - relativedelta(months=1)
                month_key = last_month.strftime("%Y-%m")
                
                # Запускаем polling асинхронно, не блокируя ответ
                asyncio.create_task(
                    poll_for_anomalies(month_key, chat_id, bot)
                )
                logger.info(f"Started polling for month_key={month_key} after CSV upload")
                    
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                reply_text = "❌ Ошибка обработки файла. Попробуй ещё раз."
        
        return reply_text
        
    except httpx.ConnectError:
        logger.error("Cannot connect to CFO API")
        return "❌ Не могу подключиться к API. Убедитесь, что сервис запущен."
    except Exception as e:
        logger.error(f"Error processing CSV: {e}")
        return "❌ Ошибка обработки файла. Попробуй ещё раз."


@router.message(F.document, F.document.file_name.endswith(".csv"))
async def handle_csv_upload(message: types.Message, bot: Bot, state: FSMContext):
    """Обработчик загрузки CSV файлов - первый шаг: анализ файла"""
    document = message.document
    
    await message.reply("⏳ Анализирую файл...")
    
    try:
        # Скачиваем файл
        file = await bot.get_file(document.file_id)
        file_bytes = await bot.download_file(file.file_path)
        
        # Отправляем на preview для анализа валют
        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {"file": (document.file_name, file_bytes, "text/csv")}
            response = await client.post(
                "http://cfo_api:8002/ingest/csv/preview",
                files=files
            )
            
            if response.status_code == 200:
                preview_data = response.json()
                has_uah = preview_data.get("has_uah", False)
                currencies = preview_data.get("currencies", [])
                transaction_count = preview_data.get("transaction_count", 0)
                
                logger.info(f"CSV preview: has_uah={has_uah}, currencies={currencies}, count={transaction_count}")
                
                if has_uah and "UAH" in currencies:
                    # Есть UAH транзакции - запрашиваем курс
                    await state.set_state(CSVUploadState.waiting_for_fx_rate)
                    await state.update_data(
                        file_bytes=file_bytes,
                        filename=document.file_name,
                        chat_id=message.chat.id
                    )
                    
                    reply_text = (
                        f"📊 В файле обнаружены транзакции в UAH ({transaction_count} всего).\n\n"
                        f"Для корректной работы Observer layer нужен курс UAH/USD.\n"
                        f"Введите курс (например, 39.5) или используйте /skip для пропуска конвертации.\n\n"
                        f"*Примечание:* если пропустить, метрики будут рассчитаны в UAH, "
                        f"что может повлиять на детекцию аномалий."
                    )
                    await message.reply(reply_text)
                else:
                    # Нет UAH транзакций - загружаем сразу
                    reply_text = await _process_csv_with_fx_rate(
                        file_bytes, document.file_name, 0.0, "skip",
                        message.chat.id, bot
                    )
                    await message.reply(reply_text)
            else:
                logger.error(f"Preview API error: {response.status_code} - {response.text}")
                await message.reply("❌ Ошибка анализа файла. Попробуй ещё раз.")
        
    except httpx.ConnectError:
        logger.error("Cannot connect to CFO API")
        await message.reply("❌ Не могу подключиться к API. Убедитесь, что сервис запущен.")
    except Exception as e:
        logger.error(f"Error processing CSV: {e}")
        await message.reply("❌ Ошибка обработки файла. Попробуй ещё раз.")


@router.message(Command("skip"), CSVUploadState.waiting_for_fx_rate)
async def handle_skip_fx_rate(message: types.Message, bot: Bot, state: FSMContext):
    """Обработчик команды /skip для пропуска запроса курса"""
    data = await state.get_data()
    file_bytes = data.get("file_bytes")
    filename = data.get("filename")
    chat_id = data.get("chat_id", message.chat.id)
    
    await message.reply("⏳ Загружаю файл без конвертации валют...")
    
    reply_text = await _process_csv_with_fx_rate(
        file_bytes, filename, 0.0, "skip", chat_id, bot
    )
    
    await state.clear()
    await message.reply(reply_text)


@router.message(CSVUploadState.waiting_for_fx_rate)
async def handle_fx_rate_input(message: types.Message, bot: Bot, state: FSMContext):
    """Обработчик ввода курса валют"""
    try:
        # Пробуем распарсить число
        fx_rate = float(message.text.replace(",", "."))
        
        if fx_rate <= 0:
            await message.reply("❌ Курс должен быть положительным числом. Попробуйте снова.")
            return
        
        data = await state.get_data()
        file_bytes = data.get("file_bytes")
        filename = data.get("filename")
        chat_id = data.get("chat_id", message.chat.id)
        
        await message.reply(f"⏳ Загружаю файл с курсом {fx_rate} UAH/USD...")
        
        reply_text = await _process_csv_with_fx_rate(
            file_bytes, filename, fx_rate, "manual", chat_id, bot
        )
        
        await state.clear()
        await message.reply(reply_text)
        
    except ValueError:
        await message.reply("❌ Неверный формат курса. Введите число (например, 39.5) или используйте /skip.")