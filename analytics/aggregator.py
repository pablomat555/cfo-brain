from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any
from loguru import logger

from core.models import Transaction, PeriodReport


def build_period_report(
    transactions: List[Transaction], 
    rate: float | None = None, 
    rate_type: str = "split"
) -> PeriodReport:
    """
    Строит отчёт за период из списка транзакций с поддержкой мультивалютной агрегации.
    
    Args:
        transactions: Список объектов Transaction из БД
        rate: Курс конвертации USD/UAH (если rate_type == "manual")
        rate_type: "split" (раздельный отчёт по валютам) или "manual" (конвертация по курсу)
        
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
            ai_verdict=None,
            currency_breakdown=None,
            rate=rate,
            rate_type=rate_type
        )
    
    # Инициализация агрегаторов по валютам
    currency_data: Dict[str, Dict[str, Any]] = {}
    
    for tx in transactions:
        # Проверяем заполнение поля currency
        if not tx.currency or tx.currency == "UNKNOWN":
            logger.warning(f"Transaction {tx.id} has unknown currency, skipping from aggregation")
            continue
            
        amount = float(tx.amount) if isinstance(tx.amount, Decimal) else tx.amount
        currency = tx.currency
        
        # Инициализируем структуру для валюты если её ещё нет
        if currency not in currency_data:
            currency_data[currency] = {
                "total_income": 0.0,
                "total_expenses": 0.0,
                "net_savings": 0.0,
                "by_category": {},
                "by_account": {},
                "expenses_list": []
            }
        
        # Агрегация по категории
        category = tx.category or "Unknown"
        currency_data[currency]["by_category"][category] = currency_data[currency]["by_category"].get(category, 0.0) + amount
        
        # Агрегация по аккаунту
        account = tx.account or "Unknown"
        currency_data[currency]["by_account"][account] = currency_data[currency]["by_account"].get(account, 0.0) + amount
        
        # Разделение на доходы и расходы
        if amount > 0:
            currency_data[currency]["total_income"] += amount
        else:
            # Для расходов храним положительное значение для удобства
            expense_amount = abs(amount)
            currency_data[currency]["total_expenses"] += expense_amount
            currency_data[currency]["expenses_list"].append({
                "description": tx.description,
                "amount": expense_amount,
                "category": category,
                "date": tx.date.isoformat() if tx.date else None,
                "currency": currency
            })
    
    # Вычисляем net_savings для каждой валюты
    for currency, data in currency_data.items():
        data["net_savings"] = data["total_income"] - data["total_expenses"]
    
    # Логика конвертации если rate_type == "manual" и rate передан
    if rate_type == "manual" and rate is not None and rate > 0:
        # Конвертируем UAH → USD, предполагаем что основная валюта USD
        total_income_usd = 0.0
        total_expenses_usd = 0.0
        by_category_usd: Dict[str, float] = {}
        by_account_usd: Dict[str, float] = {}
        expenses_list_usd = []
        
        for currency, data in currency_data.items():
            if currency == "USD":
                # USD остаётся как есть
                total_income_usd += data["total_income"]
                total_expenses_usd += data["total_expenses"]
                
                # Агрегация по категориям
                for category, amount in data["by_category"].items():
                    by_category_usd[category] = by_category_usd.get(category, 0.0) + amount
                
                # Агрегация по аккаунтам
                for account, amount in data["by_account"].items():
                    by_account_usd[account] = by_account_usd.get(account, 0.0) + amount
                
                # Добавляем расходы
                expenses_list_usd.extend(data["expenses_list"])
                
            elif currency == "UAH":
                # Конвертируем UAH → USD
                total_income_usd += data["total_income"] / rate
                total_expenses_usd += data["total_expenses"] / rate
                
                # Агрегация по категориям с конвертацией
                for category, amount in data["by_category"].items():
                    by_category_usd[category] = by_category_usd.get(category, 0.0) + (amount / rate)
                
                # Агрегация по аккаунтам с конвертацией
                for account, amount in data["by_account"].items():
                    by_account_usd[account] = by_account_usd.get(account, 0.0) + (amount / rate)
                
                # Добавляем расходы с конвертированной суммой
                for expense in data["expenses_list"]:
                    expense_usd = expense.copy()
                    expense_usd["amount"] = expense["amount"] / rate
                    expense_usd["original_currency"] = "UAH"
                    expense_usd["original_amount"] = expense["amount"]
                    expense_usd["rate"] = rate
                    expenses_list_usd.append(expense_usd)
            else:
                # Другие валюты - пропускаем (логируем)
                logger.warning(f"Currency {currency} not supported for conversion, skipping")
        
        # Вычисление производных показателей
        net_savings_usd = total_income_usd - total_expenses_usd
        savings_rate_usd = (net_savings_usd / total_income_usd * 100) if total_income_usd > 0 else 0.0
        burn_rate_usd = total_expenses_usd
        
        # Топ-5 расходов по величине
        top_expenses_usd = sorted(expenses_list_usd, key=lambda x: x["amount"], reverse=True)[:5]
        
        # Определение месяца (берём из первой транзакции или текущий)
        month = transactions[0].date.replace(day=1) if transactions else datetime.now().replace(day=1)
        
        # Определение типа периода
        period_type = "custom"
        if transactions:
            dates = [tx.date for tx in transactions if tx.date]
            if dates:
                min_date = min(dates)
                max_date = max(dates)
                
                today = datetime.now().date()
                current_month_start = today.replace(day=1)
                if today.month == 1:
                    current_month_end = today.replace(year=today.year-1, month=12, day=31)
                else:
                    current_month_end = today.replace(day=1, month=today.month) - timedelta(days=1)
                
                if current_month_start.month == 1:
                    prev_month_start = current_month_start.replace(year=current_month_start.year-1, month=12)
                else:
                    prev_month_start = current_month_start.replace(month=current_month_start.month-1, day=1)
                prev_month_end = current_month_start - timedelta(days=1)
                
                if min_date >= current_month_start and max_date <= current_month_end:
                    period_type = "this_month"
                elif min_date >= prev_month_start and max_date <= prev_month_end:
                    period_type = "previous_month"
        
        return PeriodReport(
            total_income=round(total_income_usd, 2),
            total_expenses=round(total_expenses_usd, 2),
            net_savings=round(net_savings_usd, 2),
            savings_rate=round(savings_rate_usd, 2),
            burn_rate=round(burn_rate_usd, 2),
            by_category={k: round(v, 2) for k, v in by_category_usd.items()},
            by_account={k: round(v, 2) for k, v in by_account_usd.items()},
            top_expenses=top_expenses_usd,
            month=month,
            currency="USD",
            period_type=period_type,
            ai_verdict=None,
            currency_breakdown=None,  # В режиме manual не показываем разбивку
            rate=rate,
            rate_type=rate_type
        )
    else:
        # Режим split - возвращаем раздельный отчёт по валютам
        # Суммируем все валюты для общего отчёта (в основной валюте - UAH)
        total_income = 0.0
        total_expenses = 0.0
        by_category: Dict[str, float] = {}
        by_account: Dict[str, float] = {}
        expenses_list = []
        
        for currency, data in currency_data.items():
            total_income += data["total_income"]
            total_expenses += data["total_expenses"]
            
            # Агрегация по категориям
            for category, amount in data["by_category"].items():
                by_category[category] = by_category.get(category, 0.0) + amount
            
            # Агрегация по аккаунтам
            for account, amount in data["by_account"].items():
                by_account[account] = by_account.get(account, 0.0) + amount
            
            # Добавляем расходы
            expenses_list.extend(data["expenses_list"])
        
        # Вычисление производных показателей
        net_savings = total_income - total_expenses
        savings_rate = (net_savings / total_income * 100) if total_income > 0 else 0.0
        burn_rate = total_expenses
        
        # Топ-5 расходов по величине
        top_expenses = sorted(expenses_list, key=lambda x: x["amount"], reverse=True)[:5]
        
        # Определение месяца (берём из первой транзакции или текущий)
        month = transactions[0].date.replace(day=1) if transactions else datetime.now().replace(day=1)
        
        # Определение типа периода
        period_type = "custom"
        if transactions:
            dates = [tx.date for tx in transactions if tx.date]
            if dates:
                min_date = min(dates)
                max_date = max(dates)
                
                today = datetime.now().date()
                current_month_start = today.replace(day=1)
                if today.month == 1:
                    current_month_end = today.replace(year=today.year-1, month=12, day=31)
                else:
                    current_month_end = today.replace(day=1, month=today.month) - timedelta(days=1)
                
                if current_month_start.month == 1:
                    prev_month_start = current_month_start.replace(year=current_month_start.year-1, month=12)
                else:
                    prev_month_start = current_month_start.replace(month=current_month_start.month-1, day=1)
                prev_month_end = current_month_start - timedelta(days=1)
                
                if min_date >= current_month_start and max_date <= current_month_end:
                    period_type = "this_month"
                elif min_date >= prev_month_start and max_date <= prev_month_end:
                    period_type = "previous_month"
        
        # Подготавливаем currency_breakdown для отображения
        currency_breakdown = {}
        for currency, data in currency_data.items():
            currency_breakdown[currency] = {
                "total_income": round(data["total_income"], 2),
                "total_expenses": round(data["total_expenses"], 2),
                "net_savings": round(data["net_savings"], 2),
                "by_category": {k: round(v, 2) for k, v in data["by_category"].items()},
                "by_account": {k: round(v, 2) for k, v in data["by_account"].items()},
                "top_expenses": sorted(data["expenses_list"], key=lambda x: x["amount"], reverse=True)[:3]
            }
        
        # Определяем основную валюту (первую найденную или UAH)
        main_currency = "UAH"
        if currency_data:
            main_currency = list(currency_data.keys())[0]
        
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
            currency=main_currency,
            period_type=period_type,
            ai_verdict=None,
            currency_breakdown=currency_breakdown,
            rate=rate,
            rate_type=rate_type
        )