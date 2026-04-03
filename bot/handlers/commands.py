import httpx
from aiogram import types, Router
from aiogram.filters import Command
from loguru import logger

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    welcome_text = (
        "👋 Привет! Я CFO Brain — твой персональный финансовый директор.\n\n"
        "📊 **Как работать со мной:**\n"
        "1. Экспортируй транзакции из банковского приложения в CSV\n"
        "2. Отправь мне CSV файл\n"
        "3. Я проанализирую твои расходы и доходы\n\n"
        "📁 **Формат CSV:** Должен содержать колонки:\n"
        "Date, Description, Category, Payee, Tag, Account, Transfer Account, Amount\n\n"
        "⚡ **Доступные команды:**\n"
        "/start - это сообщение\n"
        "/status - статус системы\n\n"
        "Отправь мне CSV файл чтобы начать!"
    )
    await message.reply(welcome_text, parse_mode="Markdown")


@router.message(Command("status"))
async def cmd_status(message: types.Message):
    """Обработчик команды /status"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://cfo_api:8000/health")
            
            if response.status_code == 200:
                status_data = response.json()
                status_text = (
                    f"✅ **Статус системы:**\n"
                    f"• API: Работает\n"
                    f"• Состояние: {status_data.get('status', 'unknown')}\n"
                    f"• Версия: 0.1.0"
                )
            else:
                status_text = "❌ **API не отвечает**\nПроверьте, запущен ли сервис."
                
    except httpx.ConnectError:
        status_text = "❌ **Не могу подключиться к API**\nСервис может быть не запущен."
    except Exception as e:
        logger.error(f"Error checking status: {e}")
        status_text = f"❌ **Ошибка:** {str(e)}"
    
    await message.reply(status_text, parse_mode="Markdown")