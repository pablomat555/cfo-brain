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
from bot.i18n import i18n as t

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


# FSM States для /capital_edit (Rev 4)
class CapitalEditStates(StatesGroup):
    SelectAccount = State()
    SelectField = State()
    InputValue = State()
    FxRateInput = State()
    Confirm = State()


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
        f"💼 <b>Capital State</b> ({formatted_date})",
        f"<b>Net Worth:</b> ${format_currency_amount(state_data['total_net_worth_usd'])}",
        ""
    ]

    for bucket_name, bucket_data in state_data["by_bucket"].items():
        if bucket_data["total_usd"] > 0:
            emoji = bucket_emojis.get(bucket_name, "•")
            lines.append(f"{emoji} <b>{bucket_name.replace('_', ' ').title()}:</b> ${format_currency_amount(bucket_data['total_usd'])}")
            
            for account in bucket_data["accounts"]:
                account_name = account["account_name"]
                asset_symbol = account["asset_symbol"]
                value_usd = account["value_usd"]
                currency = account.get("currency", "USD")
                market_value = account["market_value"]
                fx_rate = account.get("fx_rate", 1.0)

                if currency in ["USD", "USDT"] or fx_rate == 1.0:
                    lines.append(f"  • {account_name} ({asset_symbol}): ${format_currency_amount(value_usd)}")
                else:
                    lines.append(f"  • {account_name} ({asset_symbol}): ${format_currency_amount(value_usd)} ({market_value:,.0f} {currency} @ {fx_rate})")
    
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
        await message.answer(formatted, parse_mode="HTML")
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            await message.answer(t("capital.state_no_snapshot"))
        else:
            await message.answer(t("capital.state_error", status_code=e.response.status_code))
    except Exception as e:
        logger.error(f"Error in /capital command: {e}")
        await message.answer(t("capital.state_generic_error"))


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
        await message.answer(t("capital.add_account_prompt"))
        return

    await state.update_data(account_name=account_name)
    await message.answer(t("capital.add_account_confirmed", account_name=account_name))
    await state.set_state(CapitalAddStates.balance)


# Шаг 2: balance
@router.message(CapitalAddStates.balance)
async def process_balance(message: Message, state: FSMContext):
    try:
        balance = float(message.text.replace(",", "."))
        if balance <= 0:
            await message.answer(t("capital.add_balance_positive"))
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
        await message.answer(t("capital.add_balance_invalid"))


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
            await message.answer(t("capital.add_fx_rate_positive"))
            return
        
        await state.update_data(fx_rate=fx_rate)
        await ask_bucket(message, state)
        
    except ValueError:
        await message.answer(t("capital.add_fx_rate_invalid"))


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
        f"<b>Подтвердите данные:</b>\n\n"
        f"• <b>Счёт:</b> {account_name}\n"
        f"• <b>Баланс:</b> {balance:,.2f} {currency}\n"
    )

    if currency not in ["USD", "USDT"]:
        confirm_text += f"• <b>Курс {currency}/USD:</b> {fx_rate}\n"

    confirm_text += (
        f"• <b>Категория:</b> {bucket_emoji} {bucket.replace('_', ' ').title()}\n"
        f"• <b>Баланс в USD:</b> ${balance_usd:,.2f}\n"
        f"• <b>Дата:</b> {date.today().isoformat()}\n\n"
        f"Всё верно?"
    )
    
    # Клавиатура подтверждения
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Сохранить", callback_data="confirm_save")
    keyboard.button(text="❌ Отмена", callback_data="confirm_cancel")
    keyboard.adjust(2)
    
    await callback_query.message.edit_text(
        confirm_text,
        parse_mode="HTML",
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
            f"✅ <b>Счёт успешно сохранён!</b>\n\n"
            f"• {data['account_name']}: ${balance_usd:,.2f}\n"
            f"• Дата: {date.today().strftime('%d %B %Y')}\n\n"
            f"Используй /capital чтобы увидеть обновлённое состояние капитала."
        )

        await callback_query.message.edit_text(
            success_text,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error saving account via API: {e}")
        await callback_query.message.edit_text(
            f"❌ Ошибка при сохранении: {str(e)}"
        )
    
    await state.clear()
    await callback_query.answer()


# Команда /capital_edit - начало FSM (Rev 4)
@router.message(Command("capital_edit"))
async def command_capital_edit(message: Message, state: FSMContext):
    """Начать процесс редактирования существующего счёта"""
    await state.clear()
    try:
        # Получаем список счетов
        response = await call_api("/capital/accounts")
        accounts = response.get("accounts", [])

        if not accounts:
            await message.answer(t("capital.edit_no_accounts"))
            return

        # Создаём клавиатуру со счетами
        keyboard = InlineKeyboardBuilder()
        for account in accounts:
            keyboard.button(text=account, callback_data=f"edit_account_{account}")
        keyboard.adjust(1)

        await message.answer(
            t("capital.edit.select_account"),
            reply_markup=keyboard.as_markup()
        )
        await state.set_state(CapitalEditStates.SelectAccount)

    except Exception as e:
        logger.error(f"Error in /capital_edit command: {e}")
        await message.answer(t("capital.edit_error"))


# Шаг 1: SelectAccount (обработка callback)
@router.callback_query(CapitalEditStates.SelectAccount, F.data.startswith("edit_account_"))
async def process_select_account(callback_query, state: FSMContext):
    account_name = callback_query.data.replace("edit_account_", "")
    await state.update_data(account_name=account_name)

    # Получаем текущие данные счёта через API
    try:
        response = await call_api(f"/capital/account_by_name?account_name={account_name}")
        account_data = response.get("account")
        if account_data:
            await state.update_data(current_account=account_data)
    except Exception as e:
        logger.warning(f"Could not fetch account details: {e}")
        # Продолжаем без текущих данных

    # Клавиатура выбора поля
    keyboard = InlineKeyboardBuilder()
    fields = [
        ("💰 Баланс", "balance"),
        ("💱 Валюта", "currency"),
        ("📊 Курс (fx_rate)", "fx_rate"),
        ("📦 Категория (bucket)", "bucket")
    ]
    for display, field in fields:
        keyboard.button(text=display, callback_data=f"edit_field_{field}")
    keyboard.adjust(2)

    await callback_query.message.edit_text(
        t("capital.edit.select_field", account_name=account_name),
        reply_markup=keyboard.as_markup()
    )
    await state.set_state(CapitalEditStates.SelectField)
    await callback_query.answer()


# Шаг 2: SelectField (обработка callback)
@router.callback_query(CapitalEditStates.SelectField, F.data.startswith("edit_field_"))
async def process_select_field(callback_query, state: FSMContext):
    field = callback_query.data.replace("edit_field_", "")
    await state.update_data(selected_field=field)

    data = await state.get_data()
    current_account = data.get("current_account", {})

    if field in ("currency", "bucket"):
        # Для currency и bucket показываем inline keyboard
        if field == "currency":
            keyboard = InlineKeyboardBuilder()
            currencies = ["USD", "USDT", "UAH", "EUR", "Other"]
            for curr in currencies:
                keyboard.button(text=curr, callback_data=f"edit_value_{curr}")
            keyboard.adjust(3)
            prompt = t("capital.edit.input_value.currency")
        else:  # bucket
            keyboard = InlineKeyboardBuilder()
            buckets = [
                ("💧 Liquid", "liquid"),
                ("🔄 Semi-liquid", "semi_liquid"),
                ("📈 Investment", "investment")
            ]
            for display, bucket_val in buckets:
                keyboard.button(text=display, callback_data=f"edit_value_{bucket_val}")
            keyboard.adjust(1)
            prompt = t("capital.edit.input_value.bucket")

        await callback_query.message.edit_text(
            prompt,
            reply_markup=keyboard.as_markup()
        )
        await state.set_state(CapitalEditStates.InputValue)
    else:
        # Для balance и fx_rate запрашиваем текстовый ввод
        prompt = t(f"capital.edit.input_value.{field}")
        await callback_query.message.edit_text(prompt)
        await state.set_state(CapitalEditStates.InputValue)

    await callback_query.answer()


# Шаг 3: InputValue (обработка callback для currency/bucket, текстовый ввод для balance/fx_rate)
@router.callback_query(CapitalEditStates.InputValue, F.data.startswith("edit_value_"))
async def process_input_value_callback(callback_query, state: FSMContext):
    value = callback_query.data.replace("edit_value_", "")
    data = await state.get_data()
    field = data.get("selected_field")

    if field == "currency":
        await state.update_data(new_currency=value)
        # Проверяем, нужен ли шаг FxRateInput
        if value in ("USD", "USDT"):
            # Пропускаем шаг FxRateInput, переходим к Confirm
            await prepare_confirm(callback_query.message, state, edit=True)
        else:
            # Запрашиваем курс
            await callback_query.message.edit_text(
                t("capital.edit.input_fx_rate", currency=value)
            )
            await state.set_state(CapitalEditStates.FxRateInput)
    elif field == "bucket":
        await state.update_data(new_bucket=value)
        await prepare_confirm(callback_query.message, state, edit=True)
    else:
        # Не должно случиться
        pass

    await callback_query.answer()


@router.message(CapitalEditStates.InputValue)
async def process_input_value_text(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/"):
        await state.clear()
        await command_capital_edit(message, state)
        return
    data = await state.get_data()
    field = data.get("selected_field")

    try:
        if field == "balance":
            value = float(message.text.replace(",", "."))
            if value <= 0:
                await message.answer(t("capital.edit.input_value.balance_positive"))
                return
            await state.update_data(new_balance=value)
        elif field == "fx_rate":
            value = float(message.text.replace(",", "."))
            if value <= 0:
                await message.answer(t("capital.edit.input_value.fx_rate_positive"))
                return
            await state.update_data(new_fx_rate=value)
        else:
            await message.answer(t("capital.edit.error"))
            return
    except ValueError:
        await message.answer(t("capital.edit.input_value.invalid_number"))
        return

    await prepare_confirm(message, state)


# Шаг 4: FxRateInput (только для non-USD/USDT валют)
@router.message(CapitalEditStates.FxRateInput)
async def process_fx_rate_input(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/"):
        await state.clear()
        await command_capital_edit(message, state)
        return
    try:
        fx_rate = float(message.text.replace(",", "."))
        if fx_rate <= 0:
            await message.answer(t("capital.edit.input_value.fx_rate_positive"))
            return
        await state.update_data(new_fx_rate=fx_rate)
        await prepare_confirm(message, state)
    except ValueError:
        await message.answer(t("capital.edit.input_value.invalid_number"))


async def prepare_confirm(message_or_callback, state: FSMContext, edit: bool = False):
    """Подготовка подтверждения с diff"""
    data = await state.get_data()
    current_account = data.get("current_account", {})
    field = data.get("selected_field")

    # Собираем diff
    diff_lines = []
    if field == "balance":
        old = current_account.get("balance", 0)
        new = data.get("new_balance")
        diff_lines.append(f"💰 Баланс: {old:,.2f} → {new:,.2f}")
    elif field == "currency":
        old = current_account.get("currency", "USD")
        new = data.get("new_currency")
        diff_lines.append(f"💱 Валюта: {old} → {new}")
        # Если есть new_fx_rate, показываем его
        new_fx = data.get("new_fx_rate")
        if new_fx is not None:
            diff_lines.append(f"📊 Курс: {new_fx}")
    elif field == "fx_rate":
        old = current_account.get("fx_rate", 1.0)
        new = data.get("new_fx_rate")
        diff_lines.append(f"📊 Курс: {old} → {new}")
    elif field == "bucket":
        old = current_account.get("bucket", "liquid")
        new = data.get("new_bucket")
        bucket_names = {"liquid": "💧 Liquid", "semi_liquid": "🔄 Semi-liquid", "investment": "📈 Investment"}
        old_display = bucket_names.get(old, old)
        new_display = bucket_names.get(new, new)
        diff_lines.append(f"📦 Категория: {old_display} → {new_display}")

    diff_text = "\n".join(diff_lines)

    confirm_text = t("capital.edit.confirm", diff=diff_text)

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Сохранить", callback_data="edit_confirm_save")
    keyboard.button(text="❌ Отмена", callback_data="edit_confirm_cancel")
    keyboard.adjust(2)

    if edit:
        await message_or_callback.edit_text(confirm_text, parse_mode="HTML", reply_markup=keyboard.as_markup())
    else:
        await message_or_callback.answer(confirm_text, parse_mode="HTML", reply_markup=keyboard.as_markup())

    await state.set_state(CapitalEditStates.Confirm)


# Шаг 5: Confirm (обработка callback)
@router.callback_query(CapitalEditStates.Confirm, F.data.in_(["edit_confirm_save", "edit_confirm_cancel"]))
async def process_confirm(callback_query, state: FSMContext):
    if callback_query.data == "edit_confirm_cancel":
        await callback_query.message.edit_text(t("capital.edit.cancelled"))
        await state.clear()
        await callback_query.answer()
        return

    data = await state.get_data()
    account_id = data.get("current_account", {}).get("id")
    if not account_id:
        await callback_query.message.edit_text(t("capital.edit.not_found"))
        await state.clear()
        await callback_query.answer()
        return

    # Формируем payload для PATCH
    payload = {}
    field = data.get("selected_field")
    if field == "balance":
        payload["balance"] = data.get("new_balance")
    elif field == "currency":
        payload["currency"] = data.get("new_currency")
        # fx_rate может быть передан отдельно, если был шаг FxRateInput
        new_fx = data.get("new_fx_rate")
        if new_fx is not None:
            payload["fx_rate"] = new_fx
    elif field == "fx_rate":
        payload["fx_rate"] = data.get("new_fx_rate")
    elif field == "bucket":
        payload["bucket"] = data.get("new_bucket")

    try:
        # Вызываем PATCH API
        response = await call_api(f"/capital/account/{account_id}", method="PATCH", json_data=payload)

        # Успех
        success_text = t("capital.edit.saved", account_name=data.get("account_name"))
        await callback_query.message.edit_text(success_text, parse_mode="HTML")

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            await callback_query.message.edit_text(t("capital.edit.conflict"))
        elif e.response.status_code == 404:
            await callback_query.message.edit_text(t("capital.edit.not_found"))
        else:
            logger.error(f"API error {e.response.status_code}: {e.response.text}")
            await callback_query.message.edit_text(t("capital.edit.error"))
    except Exception as e:
        logger.error(f"Error updating account via API: {e}")
        await callback_query.message.edit_text(t("capital.edit.error"))

    await state.clear()
    await callback_query.answer()


# Отмена FSM по кнопке ❌ (обработка callback)
@router.callback_query(F.data == "edit_confirm_cancel")
async def cancel_edit(callback_query, state: FSMContext):
    await callback_query.message.edit_text(t("capital.edit.cancelled"))
    await state.clear()
    await callback_query.answer()


# Отмена FSM по команде /cancel
@router.message(Command("cancel"))
async def command_cancel(message: Message, state: FSMContext):
    """Отменить текущий FSM процесс"""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(t("capital.cancel_no_process"))
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
            await message.answer(t("capital.positions_empty"))
            return
        
        # Группируем по дате
        by_date = {}
        for pos in positions:
            as_of_date = pos["as_of_date"]
            if as_of_date not in by_date:
                by_date[as_of_date] = []
            by_date[as_of_date].append(pos)
        
        # Формируем сообщение
        lines = ["📊 <b>Позиции портфеля</b>"]
        for date_str, pos_list in sorted(by_date.items(), reverse=True):
            lines.append(f"\n<b>{date_str}</b>")
            total_usd = sum(p["market_value_usd"] for p in pos_list)
            lines.append(f"Всего: ${total_usd:,.2f}")
            for pos in pos_list:
                lines.append(
                    f"• {pos['account_name']} – {pos['asset_symbol']}: "
                    f"{pos['quantity']} × ${pos['market_value_usd']/pos['quantity']:,.2f} = "
                    f"${pos['market_value_usd']:,.2f} ({pos['asset_type']})"
                )

        await message.answer("\n".join(lines), parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        await message.answer(t("capital.positions_error", error=str(e)))


@router.message(Command("position_add"))
async def command_position_add(message: Message, state: FSMContext):
    """Начать добавление позиции портфеля"""
    await message.answer(
        "📝 <b>Добавление позиции портфеля</b>\n\n"
        "Введите название счёта (например, IBKR, Bybit, Trust Wallet):",
        parse_mode="HTML"
    )
    await state.set_state(PositionAddStates.account_name)


@router.message(PositionAddStates.account_name)
async def process_position_account_name(message: Message, state: FSMContext):
    await state.update_data(account_name=message.text.strip())
    await message.answer(t("capital.position_add_account_prompt"))
    await state.set_state(PositionAddStates.asset_symbol)


@router.message(PositionAddStates.asset_symbol)
async def process_position_asset_symbol(message: Message, state: FSMContext):
    await state.update_data(asset_symbol=message.text.strip().upper())
    await message.answer(t("capital.position_add_quantity_prompt"))
    await state.set_state(PositionAddStates.quantity)


@router.message(PositionAddStates.quantity)
async def process_position_quantity(message: Message, state: FSMContext):
    try:
        quantity = float(message.text.replace(",", "."))
        if quantity <= 0:
            await message.answer(t("capital.position_add_quantity_positive"))
            return
        await state.update_data(quantity=quantity)
        await message.answer(t("capital.position_add_market_value_prompt"))
        await state.set_state(PositionAddStates.market_value)
    except ValueError:
        await message.answer(t("capital.position_add_quantity_invalid"))


@router.message(PositionAddStates.market_value)
async def process_position_market_value(message: Message, state: FSMContext):
    try:
        market_value = float(message.text.replace(",", "."))
        if market_value <= 0:
            await message.answer(t("capital.position_add_market_value_positive"))
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
        await message.answer(t("capital.position_add_market_value_invalid"))


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
            await message.answer(t("capital.position_add_fx_rate_positive"))
            return
        await state.update_data(fx_rate=fx_rate)
        await message.answer(
            "Введите дату позиции (YYYY-MM-DD) или нажмите /skip для сегодняшней:"
        )
        await state.set_state(PositionAddStates.as_of_date)
    except ValueError:
        await message.answer(t("capital.position_add_fx_rate_invalid"))


@router.message(PositionAddStates.as_of_date)
async def process_position_as_of_date(message: Message, state: FSMContext):
    if message.text == "/skip":
        as_of_date = date.today().isoformat()
    else:
        try:
            datetime.strptime(message.text, "%Y-%m-%d")
            as_of_date = message.text
        except ValueError:
            await message.answer(t("capital.position_add_date_invalid"))
            return
    
    await state.update_data(as_of_date=as_of_date)
    
    # Показать подтверждение
    data = await state.get_data()
    confirm_text = (
        f"<b>Подтвердите добавление позиции:</b>\n\n"
        f"• <b>Счёт:</b> {data['account_name']}\n"
        f"• <b>Актив:</b> {data['asset_symbol']}\n"
        f"• <b>Количество:</b> {data['quantity']}\n"
        f"• <b>Стоимость:</b> {data['market_value']} {data['currency']}\n"
        f"• <b>Курс к USD:</b> {data.get('fx_rate', 1.0)}\n"
        f"• <b>Дата:</b> {data['as_of_date']}\n\n"
        f"Сохранить позицию?"
    )
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Сохранить", callback_data="position_confirm_save")
    keyboard.button(text="❌ Отмена", callback_data="position_confirm_cancel")
    keyboard.adjust(2)
    
    await message.answer(
        confirm_text,
        parse_mode="HTML",
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
            f"✅ <b>Позиция добавлена!</b>\n\n"
            f"• {response['account_name']} – {response['asset_symbol']}\n"
            f"• Тип: {response['asset_type']}\n"
            f"• Ликвидность: {response['liquidity_bucket']}\n"
            f"• Стоимость в USD: ${response['market_value_usd']:,.2f}\n\n"
            f"Используй /positions чтобы увидеть все позиции."
        )

        await callback_query.message.edit_text(
            success_text,
            parse_mode="HTML"
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
