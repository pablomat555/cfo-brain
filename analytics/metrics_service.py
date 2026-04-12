from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text
from loguru import logger

from core.models import Transaction, UploadSession
from core.database import SessionLocal


def recalculate(month_key: str) -> None:
    """
    Пересчитывает метрики за указанный месяц и сохраняет в таблицы monthly_metrics и category_metrics.
    
    Args:
        month_key: Строка в формате 'YYYY-MM'
    
    Raises:
        Exception: В случае ошибки БД или расчётов
    """
    db = SessionLocal()
    try:
        # Парсим month_key
        year, month = map(int, month_key.split('-'))
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        # Получаем транзакции за месяц
        transactions = db.query(Transaction).filter(
            Transaction.date >= start_date,
            Transaction.date < end_date
        ).all()
        
        if not transactions:
            logger.warning(f"No transactions found for month {month_key}, skipping metrics calculation")
            return
        
        # Получаем последний upload_session для fx_rate и rate_type
        # ВНИМАНИЕ: UploadSession в текущей реализации не содержит fx_rate и rate_type
        # Это наблюдение вне scope, используем значения по умолчанию
        upload_session = db.query(UploadSession).order_by(UploadSession.uploaded_at.desc()).first()
        
        fx_rate = 0.0
        rate_type = "skip"
        
        if upload_session:
            # TODO: В будущем добавить fx_rate и rate_type в UploadSession
            # Пока используем значения по умолчанию
            logger.info(f"Using default fx_rate={fx_rate}, rate_type={rate_type} for month {month_key}")
        else:
            logger.warning(f"No upload sessions found, using default fx_rate={fx_rate}, rate_type={rate_type}")
        
        # Рассчитываем метрики
        total_income = 0.0
        total_spent = 0.0
        category_totals: Dict[str, float] = {}
        category_counts: Dict[str, int] = {}
        
        for tx in transactions:
            amount = float(tx.amount) if isinstance(tx.amount, Decimal) else tx.amount
            
            # Определяем категорию
            category = tx.category or "Unknown"
            
            # Агрегируем по категории
            category_totals[category] = category_totals.get(category, 0.0) + (abs(amount) if amount < 0 else amount)
            category_counts[category] = category_counts.get(category, 0) + 1
            
            # Разделяем доходы и расходы
            if amount > 0:
                total_income += amount
            else:
                total_spent += abs(amount)
        
        # Конвертируем в USD если rate_type == 'manual' и fx_rate > 0
        if rate_type == "manual" and fx_rate > 0:
            # Предполагаем что транзакции в UAH, конвертируем в USD
            total_income_usd = total_income / fx_rate if total_income > 0 else 0.0
            total_spent_usd = total_spent / fx_rate if total_spent > 0 else 0.0
            
            # Конвертируем категории
            category_totals_usd: Dict[str, float] = {}
            for category, total in category_totals.items():
                category_totals_usd[category] = total / fx_rate if total != 0 else 0.0
            
            # Используем конвертированные значения
            total_income = total_income_usd
            total_spent = total_spent_usd
            category_totals = category_totals_usd
        elif rate_type == "skip":
            # В режиме skip метрики не конвертируются, но сохраняются как есть
            # В monthly_metrics будет fx_rate = 0.0
            pass
        else:
            # split mode или неизвестный rate_type - используем как есть
            pass
        
        # Рассчитываем savings_rate
        savings_rate = 0.0
        if total_income > 0:
            savings_rate = ((total_income - total_spent) / total_income) * 100
        
        # Burn rate = total_spent (уже в USD если конвертировано)
        burn_rate = total_spent
        
        # Подготавливаем данные для upsert в monthly_metrics
        # Используем raw SQL для upsert (SQLite поддерживает INSERT OR REPLACE)
        updated_at = datetime.utcnow().isoformat()
        
        # Upsert monthly_metrics
        db.execute(
            text("""
            INSERT OR REPLACE INTO monthly_metrics
            (month_key, total_spent, total_income, savings_rate, burn_rate, currency, fx_rate, rate_type, tx_count, updated_at)
            VALUES (:month_key, :total_spent, :total_income, :savings_rate, :burn_rate, :currency, :fx_rate, :rate_type, :tx_count, :updated_at)
            """),
            {
                "month_key": month_key,
                "total_spent": total_spent,
                "total_income": total_income,
                "savings_rate": savings_rate,
                "burn_rate": burn_rate,
                "currency": "USD",
                "fx_rate": fx_rate,
                "rate_type": rate_type,
                "tx_count": len(transactions),
                "updated_at": updated_at
            }
        )
        
        # Upsert category_metrics
        for category, total in category_totals.items():
            db.execute(
                text("""
                INSERT OR REPLACE INTO category_metrics
                (month_key, category, total, tx_count)
                VALUES (:month_key, :category, :total, :tx_count)
                """),
                {
                    "month_key": month_key,
                    "category": category,
                    "total": total,
                    "tx_count": category_counts.get(category, 0)
                }
            )
        
        db.commit()
        logger.info(f"Recalculated metrics for {month_key}: {len(transactions)} transactions, {len(category_totals)} categories")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error recalculating metrics for {month_key}: {e}")
        raise
    finally:
        db.close()