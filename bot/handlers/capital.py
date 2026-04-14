from datetime import datetime, date
from typing import Dict, Any
import httpx
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from core.config import get_settings

router = Router()
settings = get_settings()
API_BASE_URL = f"http://cfo_api:{settings.api_port}"


# FSM States для /capital_add
class CapitalAddStates(StatesGroup):
    account_name = State()
    balance = State()
    currency = State()
    fx_rate = State()
    bucket = State()
    confirm = State()


# FSM States для /capital_edit
class CapitalEditStates(StatesGroup):
    select_account = State()
    new_balance = State()
    confirm = State()


# FSM States для /position_add
class PositionAddStates(StatesGroup):
    account_name = State()
    asset_symbol = State()
    quantity = State()
    market_value = State()
    currency = State()
    fx_rate = State()
    as_of_date = State()
    confirm = State()


# FSM States для /position_edit
class PositionEditStates(StatesGroup):
    select_position = State()
    new_quantity = State()
    new_market_value = State()
    confirm = State()


# Вспомогательные функции
async def call_api(endpoint: str, method: str = "GET", json_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Вызов API эндпоинта"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{API_BASE_URL}{endpoint}"
            
            if method == "GET":
                response = await client.get(url)
            elif method == "POST":
                response = await client.post(url, json=json_data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
            
    except httpx.HTTPStatusError as e:
        logger.error(f"API error {e.response.status_code}: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Error calling API {endpoint}: {e}")
        raise


def format_currency_amount(amount: float) -> str:
    """Форматирует сумму валюты с разделителями"""
    return f"{amount:,.2f}".replace(",", " ").replace(".", ",")


def format_capital_state(state_data: Dict[str, Any]) -> str:
    """Форматирует состояние капитала для отображения в Telegram"""
    as_of_date = datetime.strptime(state_data["as_of_date"], "%Y-%m-%d").date()
    formatted_date = as_of_date.strftime("%d %B %Y").replace(" 0", " ")
    
    # Эмодзи для bucket
    bucket_emojis = {
        "liquid": "💧",
        "semi_liquid": "🔄", 
        "investment": "📈"
    }
    
    lines = [
        f"💼 *Capital State* ({formatted_date})",
        f"*Net Worth:* ${format_currency_amount(state_data['total_net_worth_usd'])}",
        ""
    ]
    
    for bucket_name, bucket_data in state_data["by_bucket"].items():
        if bucket_data["total_usd"] > 0:
            emoji = bucket_emojis.get(bucket_name, "•")
            lines.append(f"{emoji} *{bucket_name.replace('_', ' ').title()}:* ${format_currency_amount(bucket_data['total_usd'])}")
            
            for account in bucket_data["accounts"]:
                account_name = account["account_name"]
                balance_usd = account["balance_usd"]
                currency = account["currency"]
                balance = account["balance"]
                
                if currency in ["USD", "USDT"]:
                    lines.append(f"  • {account_name}: ${format_currency_amount(balance_usd)}")
                else:
                    fx_rate = account["fx_rate"]
                    lines.append(f"  • {account_name}: ${format_currency_amount(balance_usd)} ({balance:,.0f} {currency} @ {fx_rate})")
    
    return "\n".join(lines)


# Команда /capital
@router.message(Command("capital"))
async def command_capital(message: Message):
    """Показать текущее состояние капитала"""
    try:
        # Получаем состояние капитала
        state_data = await call_api("/capital/state")
        
        # Форматируем и отправляем
        formatted = format_capital_state(state_data)
        await message.answer(formatted, parse_mode="Markdown")
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            await message.answer("Нет снимка капитала. Используй /capital_add")
        else:
            await message.answer(f"Ошибка при получении данных: {e.response.status_code}")
    except Exception as e:
        logger.error(f"Error in /capital command: {e}")
        await message.answer("Произошла ошибка при получении состояния капитала")


# Команда /capital_add - начало FSM
@router.message(Command("capital_add"))
async def command_capital_add(message: Message, state: FSMContext):
    """Начать процесс добавления нового счёта"""
    await message.answer(
        "Добавление нового счёта в капитальный снапшот.\n"
        "Введите название счёта (например: Payoneer, Monobank UAH, Bybit):",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(CapitalAddStates.account_name)


# Шаг 1: account_name
@router.message(CapitalAddStates.account_name)
async def process_account_name(message: Message, state: FSMContext):
    account_name = message.text.strip()
    if not account_name:
        await message.answer("Пожалуйста, введите корректное название счёта:")
        return
    
    await state.update_data(account_name=account_name)
    await message.answer(f"Счёт: {account_name}\nВведите баланс (число):")
    await state.set_state(CapitalAddStates.balance)


# Шаг 2: balance
@router.message(CapitalAddStates.balance)
async def process_balance(message: Message, state: FSMContext):
    try:
        balance = float(message.text.replace(",", "."))
        if balance <= 0:
            await message.answer("Баланс должен быть положительным числом. Введите снова:")
            return
        
        await state.update_data(balance=balance)
        
        # Создаём клавиатуру с валютами
        keyboard = InlineKeyboardBuilder()
        currencies = ["USD", "USDT", "UAH", "EUR", "Other"]
        for currency in currencies:
            keyboard.button(text=currency, callback_data=f"currency_{currency}")
        keyboard.adjust(3, 2)
        
        await message.answer(
            f"Баланс: {balance:,.2f}\nВыберите валюту:",
            reply_markup=keyboard.as_markup()
        )
        await state.set_state(CapitalAddStates.currency)
        
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число (например: 4200 или 180000):")


# Шаг 3: currency (обработка callback)
@router.callback_query(CapitalAddStates.currency, F.data.startswith("currency_"))
async def process_currency(callback_query, state: FSMContext):
    currency = callback_query.data.replace("currency_", "")
    await state.update_data(currency=currency)
    
    await callback_query.message.edit_text(f"Валюта: {currency}")
    
    # Если валюта не USD/USDT, запрашиваем курс
    if currency in ["USD", "USDT"]:
        await state.update_data(fx_rate=1.0)
        await ask_bucket(callback_query.message, state)
    else:
        await callback_query.message.answer(
            f"Курс {currency}/USD? (например, для UAH введите 43.85):"
        )
        await state.set_state(CapitalAddStates.fx_rate)
    
    await callback_query.answer()


# Шаг 4: fx_rate (только для не-USD валют)
@router.message(CapitalAddStates.fx_rate)
async def process_fx_rate(message: Message, state: FSMContext):
    try:
        fx_rate = float(message.text.replace(",", "."))
        if fx_rate <= 0:
            await message.answer("Курс должен быть положительным числом. Введите снова:")
            return
        
        await state.update_data(fx_rate=fx_rate)
        await ask_bucket(message, state)
        
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число (например: 43.85):")


def get_bucket_keyboard():
    """Создаёт клавиатуру для выбора bucket"""
    keyboard = InlineKeyboardBuilder()
    buckets = [
        ("💧 Liquid", "liquid"),
        ("🔄 Semi-liquid", "semi_liquid"),
        ("📈 Investment", "investment")
    ]
    for display_name, bucket_value in buckets:
        keyboard.button(text=display_name, callback_data=f"bucket_{bucket_value}")
    keyboard.adjust(1)
    return keyboard


async def ask_bucket(message: Message, state: FSMContext):
    """Запрашивает bucket (категорию ликвидности)"""
    keyboard = get_bucket_keyboard()
    await message.answer(
        "Выберите категорию ликвидности:",
        reply_markup=keyboard.as_markup()
    )
    await state.set_state(CapitalAddStates.bucket)


# Шаг 5: bucket (обработка callback)
@router.callback_query(CapitalAddStates.bucket, F.data.startswith("bucket_"))
async def process_bucket(callback_query, state: FSMContext):
    bucket = callback_query.data.replace("bucket_", "")
    await state.update_data(bucket=bucket)
    
    # Получаем все данные
    data = await state.get_data()
    
    # Форматируем для подтверждения
    account_name = data["account_name"]
    balance = data["balance"]
    currency = data["currency"]
    fx_rate = data.get("fx_rate", 1.0)
    
    # Вычисляем баланс в USD
    balance_usd = balance * fx_rate
    
    # Эмодзи для bucket
    bucket_emojis = {
        "liquid": "💧",
        "semi_liquid": "🔄",
        "investment": "📈"
    }
    bucket_emoji = bucket_emojis.get(bucket, "•")
    
    confirm_text = (
        f"*Подтвердите данные:*\n\n"
        f"• *Счёт:* {account_name}\n"
        f"• *Баланс:* {balance:,.2f} {currency}\n"
    )
    
    if currency not in ["USD", "USDT"]:
        confirm_text += f"• *Курс {currency}/USD:* {fx_rate}\n"
    
    confirm_text += (
        f"• *Категория:* {bucket_emoji} {bucket.replace('_', ' ').title()}\n"
        f"• *Баланс в USD:* ${balance_usd:,.2f}\n"
        f"• *Дата:* {date.today().isoformat()}\n\n"
        f"Всё верно?"
    )
    
    # Клавиатура подтверждения
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Сохранить", callback_data="confirm_save")
    keyboard.button(text="❌ Отмена", callback_data="confirm_cancel")
    keyboard.adjust(2)
    
    await callback_query.message.edit_text(
        confirm_text,
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )
    await state.set_state(CapitalAddStates.confirm)
    await callback_query.answer()


# Шаг 6: confirm (обработка callback)
@router.callback_query(CapitalAddStates.confirm, F.data.in_(["confirm_save", "confirm_cancel"]))
async def process_confirm(callback_query, state: FSMContext):
    if callback_query.data == "confirm_cancel":
        await callback_query.message.edit_text("❌ Добавление счёта отменено.")
        await state.clear()
        await callback_query.answer()
        return
    
    # Сохраняем данные через API
    data = await state.get_data()
    
    # Подготавливаем данные для API
    account_data = {
        "account_name": data["account_name"],
        "balance": data["balance"],
        "currency": data["currency"],
        "fx_rate": data.get("fx_rate", 1.0),
        "bucket": data["bucket"],
        "as_of_date": date.today().isoformat()
    }
    
    try:
        # Вызываем API
        response = await call_api("/capital/account", method="POST", json_data=account_data)
        
        # Формируем сообщение об успехе
        balance_usd = response["balance_usd"]
        success_text = (
            f"✅ *Счёт успешно сохранён!*\n\n"
            f"• {data['account_name']}: ${balance_usd:,.2f}\n"
            f"• Дата: {date.today().strftime('%d %B %Y')}\n\n"
            f"Используй /capital чтобы увидеть обновлённое состояние капитала."
        )
        
        await callback_query.message.edit_text(
            success_text,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error saving account via API: {e}")
        await callback_query.message.edit_text(
            f"❌ Ошибка при сохранении: {str(e)}"
        )
    
    await state.clear()
    await callback_query.answer()


# Команда /capital_edit - начало FSM
@router.message(Command("capital_edit"))
async def command_capital_edit(message: Message, state: FSMContext):
    """Начать процесс редактирования существующего счёта"""
    try:
        # Получаем список счетов
        response = await call_api("/capital/accounts")
        accounts = response.get("accounts", [])
        
        if not accounts:
            await message.answer("Нет доступных счетов для редактирования. Сначала добавьте счёт через /capital_add")
            return
        
        # Создаём клавиатуру со счетами
        keyboard = InlineKeyboardBuilder()
        for account in accounts:
            keyboard.button(text=account, callback_data=f"edit_account_{account}")
        keyboard.adjust(1)
        
        await message.answer(
            "Выберите счёт для редактирования:",
            reply_markup=keyboard.as_markup()
        )
        await state.set_state(CapitalEditStates.select_account)
        
    except Exception as e:
        logger.error(f"Error in /capital_edit command: {e}")
        await message.answer("Произошла ошибка при получении списка счетов")


# Шаг 1: select_account (обработка callback)
@router.callback_query(CapitalEditStates.select_account, F.data.startswith("edit_account_"))
async def process_edit_account(callback_query, state: FSMContext):
    account_name = callback_query.data.replace("edit_account_", "")
    await state.update_data(account_name=account_name)
    
    # TODO: Здесь можно получить текущие данные счёта для отображения
    # Пока просто запрашиваем новый баланс
    await callback_query.message.edit_text(
        f"Редактирование счёта: {account_name}\n"
        f"Введите новый баланс:"
    )
    await state.set_state(CapitalEditStates.new_balance)
    await callback_query.answer()


# Шаг 2: new_balance
@router.message(CapitalEditStates.new_balance)
async def process_edit_balance(message: Message, state: FSMContext):
    try:
        new_balance = float(message.text.replace(",", "."))
        if new_balance <= 0:
            await message.answer("Баланс должен быть положительным числом. Введите снова:")
            return
        
        data = await state.get_data()
        account_name = data["account_name"]
        
        # TODO: Здесь можно получить остальные данные счёта из БД
        # Пока используем дефолтные значения
        edit_data = {
            "account_name": account_name,
            "balance": new_balance,
            "currency": "USD",  # Дефолт
            "fx_rate": 1.0,     # Дефолт
            "bucket": "liquid", # Дефолт
            "as_of_date": date.today().isoformat()
        }
        
        await state.update_data(edit_data=edit_data)
        
        # Показываем подтверждение
        confirm_text = (
            f"*Подтвердите обновление:*\n\n"
            f"• *Счёт:* {account_name}\n"
            f"• *Новый баланс:* {new_balance:,.2f} USD\n"
            f"• *Дата:* {date.today().isoformat()}\n\n"
            f"Обновить запись?"
        )
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="✅ Обновить", callback_data="edit_confirm_save")
        keyboard.button(text="❌ Отмена", callback_data="edit_confirm_cancel")
        keyboard.adjust(2)
        
        await message.answer(
            confirm_text,
            parse_mode="Markdown",
            reply_markup=keyboard.as_markup()
        )
        await state.set_state(CapitalEditStates.confirm)
        
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число (например: 4200 или 180000):")


# Шаг 3: confirm (обработка callback)
@router.callback_query(CapitalEditStates.confirm, F.data.in_(["edit_confirm_save", "edit_confirm_cancel"]))
async def process_edit_confirm(callback_query, state: FSMContext):
    if callback_query.data == "edit_confirm_cancel":
        await callback_query.message.edit_text("❌ Редактирование отменено.")
        await state.clear()
        await callback_query.answer()
        return
    
    # Сохраняем данные через API
    data = await state.get_data()
    edit_data = data.get("edit_data")
    
    if not edit_data:
        await callback_query.message.edit_text("❌ Ошибка: данные не найдены.")
        await state.clear()
        await callback_query.answer()
        return
    
    try:
        # Вызываем API для обновления
        response = await call_api("/capital/account", method="POST", json_data=edit_data)
        
        # Формируем сообщение об успехе
        balance_usd = response["balance_usd"]
        success_text = (
            f"✅ *Счёт успешно обновлён!*\n\n"
            f"• {edit_data['account_name']}: ${balance_usd:,.2f}\n"
            f"• Дата: {date.today().strftime('%d %B %Y')}\n\n"
            f"Используй /capital чтобы увидеть обновлённое состояние капитала."
        )
        
        await callback_query.message.edit_text(
            success_text,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error updating account via API: {e}")
        await callback_query.message.edit_text(
            f"❌ Ошибка при обновлении: {str(e)}"
        )
    
    await state.clear()
    await callback_query.answer()


# Отмена FSM по команде /cancel
@router.message(Command("cancel"))
async def command_cancel(message: Message, state: FSMContext):
    """Отменить текущий FSM процесс"""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нет активного процесса для отмены.")
        return
    
    await state.clear()
    await message.answer(
        "Процесс отменён.",
        reply_markup=ReplyKeyboardRemove()
    )


# ============================================
# Команды для работы с позициями портфеля
# ============================================

@router.message(Command("positions"))
async def command_positions(message: Message):
    """Показать список позиций портфеля"""
    try:
        response = await call_api("/capital/positions", method="GET")
        positions = response.get("positions", [])
        
        if not positions:
            await message.answer("📭 Нет позиций портфеля. Добавьте первую через /position_add")
            return
        
        # Группируем по дате
        by_date = {}
        for pos in positions:
            as_of_date = pos["as_of_date"]
            if as_of_date not in by_date:
                by_date[as_of_date] = []
            by_date[as_of_date].append(pos)
        
        # Формируем сообщение
        lines = ["📊 *Позиции портфеля*"]
        for date_str, pos_list in sorted(by_date.items(), reverse=True):
            lines.append(f"\n*{date_str}*")
            total_usd = sum(p["market_value_usd"] for p in pos_list)
            lines.append(f"Всего: ${total_usd:,.2f}")
            for pos in pos_list:
                lines.append(
                    f"• {pos['account_name']} – {pos['asset_symbol']}: "
                    f"{pos['quantity']} × ${pos['market_value_usd']/pos['quantity']:,.2f} = "
                    f"${pos['market_value_usd']:,.2f} ({pos['asset_type']})"
                )
        
        await message.answer("\n".join(lines), parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        await message.answer(f"❌ Ошибка при получении позиций: {str(e)}")


@router.message(Command("position_add"))
async def command_position_add(message: Message, state: FSMContext):
    """Начать добавление позиции портфеля"""
    await message.answer(
        "📝 *Добавление позиции портфеля*\n\n"
        "Введите название счёта (например, IBKR, Bybit, Trust Wallet):",
        parse_mode="Markdown"
    )
    await state.set_state(PositionAddStates.account_name)


@router.message(PositionAddStates.account_name)
async def process_position_account_name(message: Message, state: FSMContext):
    await state.update_data(account_name=message.text.strip())
    await message.answer("Введите символ актива (например, BTC, USDT, VOO):")
    await state.set_state(PositionAddStates.asset_symbol)


@router.message(PositionAddStates.asset_symbol)
async def process_position_asset_symbol(message: Message, state: FSMContext):
    await state.update_data(asset_symbol=message.text.strip().upper())
    await message.answer("Введите количество (например, 0.5):")
    await state.set_state(PositionAddStates.quantity)


@router.message(PositionAddStates.quantity)
async def process_position_quantity(message: Message, state: FSMContext):
    try:
        quantity = float(message.text.replace(",", "."))
        if quantity <= 0:
            await message.answer("Количество должно быть положительным. Введите снова:")
            return
        await state.update_data(quantity=quantity)
        await message.answer("Введите рыночную стоимость (в валюте актива):")
        await state.set_state(PositionAddStates.market_value)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число:")


@router.message(PositionAddStates.market_value)
async def process_position_market_value(message: Message, state: FSMContext):
    try:
        market_value = float(message.text.replace(",", "."))
        if market_value <= 0:
            await message.answer("Стоимость должна быть положительной. Введите снова:")
            return
        await state.update_data(market_value=market_value)
        
        # Предлагаем валюту кнопками
        keyboard = InlineKeyboardBuilder()
        for currency in ["USD", "USDT", "UAH", "EUR", "Other"]:
            keyboard.button(text=currency, callback_data=f"currency_{currency}")
        keyboard.adjust(3)
        
        await message.answer(
            "Выберите валюту актива:",
            reply_markup=keyboard.as_markup()
        )
        await state.set_state(PositionAddStates.currency)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число:")


@router.callback_query(PositionAddStates.currency, F.data.startswith("currency_"))
async def process_position_currency(callback_query, state: FSMContext):
    currency = callback_query.data.replace("currency_", "")
    await state.update_data(currency=currency)
    
    if currency in ["USD", "USDT"]:
        await state.update_data(fx_rate=1.0)
        await callback_query.message.edit_text(
            f"Валюта: {currency}. Курс к USD = 1.0"
        )
        await state.set_state(PositionAddStates.as_of_date)
        await callback_query.answer()
        await callback_query.message.answer(
            "Введите дату позиции (YYYY-MM-DD) или нажмите /skip для сегодняшней:"
        )
    else:
        await callback_query.message.edit_text(
            f"Валюта: {currency}. Введите курс к USD (например, 43.85 для UAH):"
        )
        await state.set_state(PositionAddStates.fx_rate)
        await callback_query.answer()


@router.message(PositionAddStates.fx_rate)
async def process_position_fx_rate(message: Message, state: FSMContext):
    try:
        fx_rate = float(message.text.replace(",", "."))
        if fx_rate <= 0:
            await message.answer("Курс должен быть положительным. Введите снова:")
            return
        await state.update_data(fx_rate=fx_rate)
        await message.answer(
            "Введите дату позиции (YYYY-MM-DD) или нажмите /skip для сегодняшней:"
        )
        await state.set_state(PositionAddStates.as_of_date)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число:")


@router.message(PositionAddStates.as_of_date)
async def process_position_as_of_date(message: Message, state: FSMContext):
    if message.text == "/skip":
        as_of_date = date.today().isoformat()
    else:
        try:
            datetime.strptime(message.text, "%Y-%m-%d")
            as_of_date = message.text
        except ValueError:
            await message.answer("Неверный формат даты. Используйте YYYY-MM-DD:")
            return
    
    await state.update_data(as_of_date=as_of_date)
    
    # Показать подтверждение
    data = await state.get_data()
    confirm_text = (
        f"*Подтвердите добавление позиции:*\n\n"
        f"• *Счёт:* {data['account_name']}\n"
        f"• *Актив:* {data['asset_symbol']}\n"
        f"• *Количество:* {data['quantity']}\n"
        f"• *Стоимость:* {data['market_value']} {data['currency']}\n"
        f"• *Курс к USD:* {data.get('fx_rate', 1.0)}\n"
        f"• *Дата:* {data['as_of_date']}\n\n"
        f"Сохранить позицию?"
    )
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Сохранить", callback_data="position_confirm_save")
    keyboard.button(text="❌ Отмена", callback_data="position_confirm_cancel")
    keyboard.adjust(2)
    
    await message.answer(
        confirm_text,
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )
    await state.set_state(PositionAddStates.confirm)


@router.callback_query(PositionAddStates.confirm, F.data.in_(["position_confirm_save", "position_confirm_cancel"]))
async def process_position_confirm(callback_query, state: FSMContext):
    if callback_query.data == "position_confirm_cancel":
        await callback_query.message.edit_text("❌ Добавление позиции отменено.")
        await state.clear()
        await callback_query.answer()
        return
    
    data = await state.get_data()
    
    # Формируем запрос к API
    position_data = {
        "account_name": data["account_name"],
        "asset_symbol": data["asset_symbol"],
        "quantity": data["quantity"],
        "market_value": data["market_value"],
        "currency": data["currency"],
        "fx_rate": data.get("fx_rate", 1.0),
        "as_of_date": data["as_of_date"],
        "source": "manual"
    }
    
    try:
        response = await call_api("/capital/position", method="POST", json_data=position_data)
        
        success_text = (
            f"✅ *Позиция добавлена!*\n\n"
            f"• {response['account_name']} – {response['asset_symbol']}\n"
            f"• Тип: {response['asset_type']}\n"
            f"• Ликвидность: {response['liquidity_bucket']}\n"
            f"• Стоимость в USD: ${response['market_value_usd']:,.2f}\n\n"
            f"Используй /positions чтобы увидеть все позиции."
        )
        
        await callback_query.message.edit_text(
            success_text,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error adding position via API: {e}")
        await callback_query.message.edit_text(
            f"❌ Ошибка при сохранении: {str(e)}"
        )
    
    await state.clear()
    await callback_query.answer()


# Команда /position_edit (упрощённая версия — требует доработки)
@router.message(Command("position_edit"))
async def command_position_edit(message: Message):
    """Редактирование позиции (заглушка)"""
    await message.answer(
        "Редактирование позиций пока не реализовано. "
        "Используйте /positions чтобы увидеть список, затем удалите и добавьте заново."
    )
