import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь для импортов
sys.path.append(str(Path(__file__).parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger

from core.config import get_settings
from bot.handlers.csv_upload import router as csv_router
from bot.handlers.commands import router as commands_router


async def main():
    """Основная функция запуска бота"""
    settings = get_settings()
    
    if not settings.telegram_token:
        logger.error("TELEGRAM_TOKEN not set in environment variables")
        sys.exit(1)
    
    # Настройка логирования
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # Инициализация бота
    bot = Bot(token=settings.telegram_token)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрация роутеров
    dp.include_router(commands_router)
    dp.include_router(csv_router)
    
    logger.info("CFO Brain bot started")
    
    # Запуск polling
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())