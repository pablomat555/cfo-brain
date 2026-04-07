from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any
from loguru import logger

from core.models import Transaction, PeriodReport


def build_period_report(transactions: List[Transaction]) -> PeriodReport:
    """
    Строит отчёт за период из списка транзакций.
    
    Args:
        transactions: Список объектов Transaction из БД
        
    Returns:
        PeriodReport объект с агрегированными данными
    """
    if not transactions:
        logger.warning("No transactions provided for monthly report")
        return PeriodReport(
            total_income=0.0,
            total_expenses=0.0,
            net_savings=0.0,
            savings_rate=0.0,
            burn_rate=0.0,
            by_category={},
            by_account={},
            top_expenses=[],
            month=datetime.now(),
            currency="UAH",
            period_type="custom",
            ai_verdict=None
        )
    
    # Инициализация агрегаторов
    total_income = 0.0
    total_expenses = 0.0
    by_category: Dict[str, float] = {}
    by_account: Dict[str, float] = {}
    expenses_list = []  # для топ расходов
    
    for tx in transactions:
        amount = float(tx.amount) if isinstance(tx.amount, Decimal) else tx.amount
        
        # Агрегация по категории
        category = tx.category or "Unknown"
        by_category[category] = by_category.get(category, 0.0) + amount
        
        # Агрегация по аккаунту
        account = tx.account or "Unknown"
        by_account[account] = by_account.get(account, 0.0) + amount
        
        # Разделение на доходы и расходы
        if amount > 0:
            total_income += amount
        else:
            # Для расходов храним положительное значение для удобства
            expense_amount = abs(amount)
            total_expenses += expense_amount
            expenses_list.append({
                "description": tx.description,
                "amount": expense_amount,
                "category": category,
                "date": tx.date.isoformat() if tx.date else None
            })
    
    # Вычисление производных показателей
    net_savings = total_income - total_expenses
    savings_rate = (net_savings / total_income * 100) if total_income > 0 else 0.0
    burn_rate = total_expenses  # сумма расходов в валюте
    
    # Топ-5 расходов по величине
    top_expenses = sorted(expenses_list, key=lambda x: x["amount"], reverse=True)[:5]
    
    # Определение месяца (берём из первой транзакции или текущий)
    month = transactions[0].date.replace(day=1) if transactions else datetime.now().replace(day=1)
    
    # Определение валюты (предполагаем UAH, но можно анализировать из транзакций)
    currency = "UAH"
    
    # Определение типа периода (custom, this_month, previous_month)
    period_type = "custom"
    if transactions:
        # Находим минимальную и максимальную даты
        dates = [tx.date for tx in transactions if tx.date]
        if dates:
            min_date = min(dates)
            max_date = max(dates)
            
            # Текущий месяц
            today = datetime.now().date()
            current_month_start = today.replace(day=1)
            if today.month == 1:
                current_month_end = today.replace(year=today.year-1, month=12, day=31)
            else:
                current_month_end = today.replace(day=1, month=today.month) - timedelta(days=1)
            
            # Предыдущий месяц
            if current_month_start.month == 1:
                prev_month_start = current_month_start.replace(year=current_month_start.year-1, month=12)
            else:
                prev_month_start = current_month_start.replace(month=current_month_start.month-1, day=1)
            prev_month_end = current_month_start - timedelta(days=1)
            
            # Проверяем, попадают ли все транзакции в текущий месяц
            if min_date >= current_month_start and max_date <= current_month_end:
                period_type = "this_month"
            # Проверяем, попадают ли все транзакции в предыдущий месяц
            elif min_date >= prev_month_start and max_date <= prev_month_end:
                period_type = "previous_month"
    
    return PeriodReport(
        total_income=round(total_income, 2),
        total_expenses=round(total_expenses, 2),
        net_savings=round(net_savings, 2),
        savings_rate=round(savings_rate, 2),
        burn_rate=round(burn_rate, 2),
        by_category={k: round(v, 2) for k, v in by_category.items()},
        by_account={k: round(v, 2) for k, v in by_account.items()},
        top_expenses=top_expenses,
        month=month,
        currency=currency,
        period_type=period_type,
        ai_verdict=None
    )