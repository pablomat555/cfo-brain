"""
Обработчик команды /digest для ручного запуска еженедельного дайджеста.
"""
import asyncio
from aiogram import types, Router, Bot
from aiogram.filters import Command
from loguru import logger

from bot.scheduler import weekly_digest

router = Router()


@router.message(Command("digest"))
async def cmd_digest(message: types.Message, bot: Bot):
    """
    Ручной запуск еженедельного дайджеста.
    Отправляет дайджест в тот же чат, откуда вызвана команда.
    """
    try:
        await message.reply("📊 Формирую дайджест...")
        await weekly_digest(bot, message.chat.id)
        logger.info(f"Manual digest sent to chat {message.chat.id}")
    except Exception as e:
        logger.error(f"Error in manual digest: {e}")
        await message.reply(f"❌ Ошибка при формировании дайджеста: {e}")