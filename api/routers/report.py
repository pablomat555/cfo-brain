from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from loguru import logger

from core.database import get_db
from core.models import Transaction, PeriodReport, UploadSession
from analytics.aggregator import build_period_report
from core.ai_verdict import generate_verdict, read_strategy_file

router = APIRouter(prefix="/report", tags=["report"])


@router.get("/period", response_model=PeriodReport)
async def get_period_report(
    from_date: Optional[str] = Query(None, alias="from", description="Начальная дата в формате YYYY-MM-DD (опционально)"),
    to_date: Optional[str] = Query(None, alias="to", description="Конечная дата в формате YYYY-MM-DD (опционально)"),
    currency: Optional[str] = Query(None, description="Фильтр по валюте (например, UAH, USD)"),
    account: Optional[str] = Query(None, description="Фильтр по счёту (например, Payoneer, Моно)"),
    rate: Optional[float] = Query(None, description="Курс конвертации USD/UAH (только для rate_type='manual')"),
    rate_type: str = Query("split", description="Тип агрегации: 'split' (раздельный отчёт) или 'manual' (конвертация по курсу)", regex="^(split|manual)$"),
    db: Session = Depends(get_db)
) -> PeriodReport:
    """
    Возвращает финансовый отчёт за период с AI-вердиктом.
    
    Параметры:
    - from: начальная дата (YYYY-MM-DD) - опционально, если не указано, используется период из последнего CSV
    - to: конечная дата (YYYY-MM-DD) - опционально, если не указано, используется период из последнего CSV
    - currency (опционально): фильтр по валюте
    - account (опционально): фильтр по счёту
    - rate (опционально): курс конвертации USD/UAH (только для rate_type='manual')
    - rate_type: тип агрегации: 'split' (раздельный отчёт по валютам) или 'manual' (конвертация по курсу)
    
    Примеры:
    - /report/period?from=2026-01-01&to=2026-01-31 (январь 2026)
    - /report/period?from=2026-01-01&to=2026-03-31 (первый квартал)
    - /report/period?from=2026-04-01&to=2026-04-15&currency=USD (первые 2 недели апреля, только USD)
    - /report/period?from=2026-04-01&to=2026-04-30&account=Payoneer (апрель, только счёт Payoneer)
    - /report/period?rate=41.5&rate_type=manual (конвертация по курсу 41.5 UAH/USD)
    - /report/period?rate_type=split (раздельный отчёт по валютам)
    - /report/period (автоопределение периода из последнего CSV, раздельный отчёт)
    """
    try:
        # Автоопределение периода если даты не указаны
        if not from_date or not to_date:
            # Получаем последний upload session
            last_session = db.query(UploadSession).order_by(UploadSession.uploaded_at.desc()).first()
            
            if last_session:
                from_dt = last_session.min_date
                to_dt = last_session.max_date
                logger.info(f"Using auto-detected period from upload session: {from_dt} to {to_dt}")
            else:
                # Fallback на текущий месяц
                today = datetime.now().date()
                first_day = today.replace(day=1)
                if today.month == 12:
                    next_month = today.replace(year=today.year + 1, month=1, day=1)
                else:
                    next_month = today.replace(month=today.month + 1, day=1)
                last_day = next_month - timedelta(days=1)
                
                from_dt = first_day
                to_dt = last_day
                logger.info(f"No upload session found, using current month: {from_dt} to {to_dt}")
        else:
            # Используем указанные даты
            try:
                from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
                to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid date format: {e}. Use YYYY-MM-DD")
        
        if from_dt > to_dt:
            raise HTTPException(status_code=400, detail="from date cannot be after to date")
        
        # Строим базовый запрос
        query = db.query(Transaction).filter(
            and_(
                Transaction.date >= from_dt,
                Transaction.date <= to_dt
            )
        )
        
        # Применяем фильтры
        if currency:
            query = query.filter(Transaction.currency == currency)
        if account:
            query = query.filter(Transaction.account == account)
        
        # Получаем транзакции
        transactions = query.all()
        logger.info(f"Found {len(transactions)} transactions for period {from_date} to {to_date}")
        
        if not transactions:
            logger.warning(f"No transactions found for period {from_date} to {to_date}")
            # Возвращаем пустой отчёт вместо ошибки
            empty_report = PeriodReport(
                total_income=0.0,
                total_expenses=0.0,
                net_savings=0.0,
                savings_rate=0.0,
                burn_rate=0.0,
                by_category={},
                by_account={},
                top_expenses=[],
                month=from_dt,
                currency=currency or "UAH",
                period_type="custom",
                ai_verdict=None,
                currency_breakdown=None,
                rate=rate,
                rate_type=rate_type
            )
            return empty_report
        
        # Строим отчёт с мультивалютной агрегацией
        report = build_period_report(transactions, rate=rate, rate_type=rate_type)
        
        # Читаем стратегию и генерируем AI вердикт
        strategy = read_strategy_file()
        ai_verdict = generate_verdict(report, strategy)
        
        # Добавляем AI вердикт в отчёт
        logger.info(f"AI verdict generated: {ai_verdict[:100]}...")
        
        # Возвращаем отчёт с вердиктом
        return report.copy(update={"ai_verdict": ai_verdict})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating monthly report: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")