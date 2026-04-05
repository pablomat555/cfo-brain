import httpx
from aiogram import types, Router, F, Bot
from aiogram.fsm.context import FSMContext
from loguru import logger

from core.config import get_settings

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
                errors = result.get("errors", 0)
                
                reply_text = (
                    f"✅ Загружено: {inserted} транзакций.\n"
                    f"📋 Дублей пропущено: {skipped}.\n"
                    f"⚠️ Ошибок: {errors}."
                )
                
                if errors > 0:
                    reply_text += "\n\nНекоторые строки не удалось обработать. Проверьте логи."
                    
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