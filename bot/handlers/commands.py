import httpx
import traceback
from aiogram import types, Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from datetime import datetime, timedelta

router = Router()


# Состояния FSM для запроса курса
class ReportStates(StatesGroup):
    waiting_for_rate = State()


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
        "/report — финансовый отчёт (автоопределение периода из последнего CSV)\n"
        "/report YYYY-MM — отчёт за конкретный месяц (например, /report 2026-03)\n\n"
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
async def cmd_report(message: types.Message, state: FSMContext):
    """Обработчик команды /report - запускает FSM для запроса курса"""
    try:
        # Парсим параметр команды (опциональный месяц в формате YYYY-MM)
        command_text = message.text.strip()
        parts = command_text.split()
        
        # Сохраняем параметры в state
        await state.update_data(
            has_month_param=len(parts) > 1,
            month_param=parts[1] if len(parts) > 1 else None
        )
        
        # Переходим в состояние ожидания курса
        await state.set_state(ReportStates.waiting_for_rate)
        await message.reply(
            "💱 Укажи курс USD/UAH для конвертации\n(или /skip для раздельного отчёта)\n\n"
            "Пример: 41.5 (означает $1 = ₴41.5)\n"
            "Или отправь /skip чтобы получить раздельный отчёт по валютам",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in cmd_report: {e}")
        await message.reply(f"❌ **Ошибка:** {str(e)}", parse_mode="Markdown")


@router.message(Command("skip"), StateFilter(ReportStates.waiting_for_rate))
async def cmd_skip_rate(message: types.Message, state: FSMContext):
    """Обработчик команды /skip - пропуск ввода курса, раздельный отчёт"""
    try:
        data = await state.get_data()
        has_month_param = data.get("has_month_param", False)
        month_param = data.get("month_param")
        
        # Формируем URL и параметры для API
        base_url, params = build_report_url(month_param, rate=None, rate_type="split")
        period_name = get_period_name(month_param)
        
        # Получаем отчёт
        report = await fetch_report(base_url, params)
        
        if report:
            # Форматируем ответ
            reply_text = format_split_report(report, period_name)
            await message.reply(reply_text, parse_mode="Markdown")
        else:
            await message.reply("❌ **Не удалось получить отчёт**\nПроверьте, запущен ли сервис.", parse_mode="Markdown")
        
        # Сбрасываем состояние
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in cmd_skip_rate: {e}\n{traceback.format_exc()}")
        await message.reply(f"❌ **Ошибка:** {str(e)}", parse_mode="Markdown")
        await state.clear()


@router.message(Command("cancel"), StateFilter(ReportStates.waiting_for_rate))
async def cmd_cancel_rate(message: types.Message, state: FSMContext):
    """Обработчик команды /cancel - отмена запроса отчёта"""
    await state.clear()
    await message.reply("❌ Запрос отчёта отменён.", parse_mode="Markdown")


@router.message(F.text, StateFilter(ReportStates.waiting_for_rate))
async def process_rate_input(message: types.Message, state: FSMContext):
    """Обработчик ввода курса"""
    try:
        # Пытаемся преобразовать ввод в число с поддержкой запятой
        rate_text = message.text.strip()
        rate_text = rate_text.replace(",", ".")
        try:
            rate = float(rate_text)
            if rate <= 0:
                raise ValueError("Курс должен быть положительным числом")
        except ValueError:
            await message.reply("❌ **Неверный формат курса.**\nВведите число (например, 41.5 или 41,5) или /skip для раздельного отчёта", parse_mode="Markdown")
            return
        
        data = await state.get_data()
        has_month_param = data.get("has_month_param", False)
        month_param = data.get("month_param")
        
        # Формируем URL и параметры для API
        base_url, params = build_report_url(month_param, rate=rate, rate_type="manual")
        period_name = get_period_name(month_param)
        
        # Получаем отчёт
        report = await fetch_report(base_url, params)
        
        if report:
            # Форматируем ответ
            reply_text = format_manual_report(report, period_name, rate)
            await message.reply(reply_text, parse_mode="Markdown")
        else:
            await message.reply("❌ **Не удалось получить отчёт**\nПроверьте, запущен ли сервис.", parse_mode="Markdown")
        
        # Сбрасываем состояние
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in process_rate_input: {e}\n{traceback.format_exc()}")
        await message.reply(f"❌ **Ошибка:** {str(e)}", parse_mode="Markdown")
        await state.clear()


# Вспомогательные функции
def build_report_url(month_param: str | None, rate: float | None, rate_type: str) -> tuple[str, dict]:
    """Строит URL и параметры для запроса отчёта"""
    base_url = "http://cfo_api:8002/report/period"
    params = {}
    
    if month_param:
        try:
            month_date = datetime.strptime(month_param, "%Y-%m").date()
            first_day = month_date.replace(day=1)
            if month_date.month == 12:
                next_month = month_date.replace(year=month_date.year + 1, month=1, day=1)
            else:
                next_month = month_date.replace(month=month_date.month + 1, day=1)
            last_day = next_month - timedelta(days=1)
            
            params["from"] = first_day.strftime("%Y-%m-%d")
            params["to"] = last_day.strftime("%Y-%m-%d")
        except ValueError:
            # Если месяц неверный, используем автоопределение
            pass
    # Если month_param нет или ошибка, API сам определит период
    
    # Добавляем параметры курса
    if rate_type == "manual" and rate:
        params["rate"] = rate
        params["rate_type"] = "manual"
    else:
        params["rate_type"] = "split"
    
    return base_url, params


def get_period_name(month_param: str | None) -> str:
    """Возвращает название периода для отображения"""
    if month_param:
        try:
            month_date = datetime.strptime(month_param, "%Y-%m").date()
            return month_date.strftime("%B %Y")
        except ValueError:
            return "автоматически определённый период"
    else:
        return "автоматически определённый период"


async def fetch_report(base_url: str, params: dict) -> dict | None:
    """Получает отчёт из API"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(base_url, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API returned {response.status_code}: {response.text}")
                return None
                
    except httpx.ConnectError:
        logger.error("Cannot connect to API")
        return None
    except Exception as e:
        logger.error(f"Error fetching report: {e}\n{traceback.format_exc()}")
        return None


def format_manual_report(report: dict, period_name: str, rate: float) -> str:
    """Форматирует единый отчёт с конвертацией"""
    total_income = report.get("total_income", 0)
    total_expenses = report.get("total_expenses", 0)
    net_savings = report.get("net_savings", 0)
    ai_verdict = report.get("ai_verdict")
    
    # Форматируем числа с разделителями тысяч
    income_formatted = f"${total_income:,.0f}" if total_income == int(total_income) else f"${total_income:,.2f}"
    expenses_formatted = f"${total_expenses:,.0f}" if total_expenses == int(total_expenses) else f"${total_expenses:,.2f}"
    savings_formatted = f"${net_savings:,.0f}" if net_savings == int(net_savings) else f"${net_savings:,.2f}"
    
    reply_text = (
        f"📊 Отчёт за {period_name} (курс $1 = ₴{rate}, manual)\n"
        f"💵 Доходы: {income_formatted}\n"
        f"💸 Расходы: {expenses_formatted}\n"
        f"💵 Чистые сбережения: {savings_formatted}"
    )
    
    # Добавляем AI вердикт если есть
    if ai_verdict:
        reply_text += f"\n\n🤖 AI вердикт:\n{ai_verdict}"
    
    return reply_text


def format_split_report(report: dict, period_name: str) -> str:
    """Форматирует раздельный отчёт по валютам"""
    total_income = report.get("total_income", 0)
    total_expenses = report.get("total_expenses", 0)
    net_savings = report.get("net_savings", 0)
    ai_verdict = report.get("ai_verdict")
    currency_breakdown = report.get("currency_breakdown")
    
    # Основной отчёт
    reply_text = f"📊 Отчёт за {period_name}\n"
    
    # Добавляем разбивку по валютам если есть
    if currency_breakdown is not None and currency_breakdown:
        for currency, data in currency_breakdown.items():
            currency_symbol = "₴" if currency == "UAH" else "$" if currency == "USD" else currency
            income = data.get("total_income", 0)
            expenses = data.get("total_expenses", 0)
            savings = data.get("net_savings", 0)
            
            # Форматируем числа
            income_formatted = f"{currency_symbol}{income:,.0f}" if income == int(income) else f"{currency_symbol}{income:,.2f}"
            expenses_formatted = f"{currency_symbol}{expenses:,.0f}" if expenses == int(expenses) else f"{currency_symbol}{expenses:,.2f}"
            savings_formatted = f"{currency_symbol}{savings:,.0f}" if savings == int(savings) else f"{currency_symbol}{savings:,.2f}"
            
            reply_text += f"\n{currency_symbol} {currency}:\n"
            reply_text += f"Доходы: {income_formatted}\n"
            reply_text += f"Расходы: {expenses_formatted}\n"
            reply_text += f"Сбережения: {savings_formatted}\n"
    else:
        # Если нет разбивки, показываем общие цифры
        main_currency = report.get("currency", "UAH")
        currency_symbol = "₴" if main_currency == "UAH" else "$" if main_currency == "USD" else main_currency
        
        income_formatted = f"{currency_symbol}{total_income:,.0f}" if total_income == int(total_income) else f"{currency_symbol}{total_income:,.2f}"
        expenses_formatted = f"{currency_symbol}{total_expenses:,.0f}" if total_expenses == int(total_expenses) else f"{currency_symbol}{total_expenses:,.2f}"
        savings_formatted = f"{currency_symbol}{net_savings:,.0f}" if net_savings == int(net_savings) else f"{currency_symbol}{net_savings:,.2f}"
        
        reply_text += f"\n{currency_symbol}:\n"
        reply_text += f"Доходы: {income_formatted}\n"
        reply_text += f"Расходы: {expenses_formatted}\n"
        reply_text += f"Сбережения: {savings_formatted}\n"
    
    # Добавляем AI вердикт если есть
    if ai_verdict:
        reply_text += f"\n🤖 AI вердикт:\n{ai_verdict}"
    
    return reply_text