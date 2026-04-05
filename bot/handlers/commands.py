import httpx
from aiogram import types, Router
from aiogram.filters import Command
from loguru import logger
from datetime import datetime, timedelta

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
        "/start — это сообщение\n"
        "/status — статус системы\n"
        "/report — финансовый отчёт за текущий месяц\n\n"
        "Отправь мне CSV файл чтобы начать!"
    )
    await message.reply(welcome_text, parse_mode="Markdown")


@router.message(Command("status"))
async def cmd_status(message: types.Message):
    """Обработчик команды /status"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://cfo_api:8002/health")
            
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


@router.message(Command("report"))
async def cmd_report(message: types.Message):
    """Обработчик команды /report"""
    try:
        # Вычисляем даты текущего месяца
        today = datetime.now().date()
        first_day = today.replace(day=1)
        # Последний день месяца: первый день следующего месяца минус один день
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)
        last_day = next_month - timedelta(days=1)
        
        from_date = first_day.strftime("%Y-%m-%d")
        to_date = last_day.strftime("%Y-%m-%d")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"http://cfo_api:8002/report/period?from={from_date}&to={to_date}"
            )
            
            if response.status_code == 200:
                report = response.json()
                total_income = report.get("total_income", 0)
                total_expenses = report.get("total_expenses", 0)
                net_savings = report.get("net_savings", 0)
                
                reply_text = (
                    f"📊 Отчёт за {first_day.strftime('%B %Y')}\n\n"
                    f"💰 Доходы: {total_income:.2f}\n"
                    f"💸 Расходы: {total_expenses:.2f}\n"
                    f"💵 Чистые сбережения: {net_savings:.2f}\n\n"
                    f"🤖 AI вердикт:\n(недоступно)"
                )
            else:
                reply_text = "❌ **Не удалось получить отчёт**\nПроверьте, запущен ли сервис."
                
    except httpx.ConnectError:
        reply_text = "❌ **Не могу подключиться к API**\nСервис может быть не запущен."
    except Exception as e:
        logger.error(f"Error fetching report: {e}")
        reply_text = f"❌ **Ошибка:** {str(e)}"
    
    await message.reply(reply_text, parse_mode="Markdown")