from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from loguru import logger
from pydantic import BaseModel
from dateutil.relativedelta import relativedelta

from core.database import get_db
from core.models import AnomalyEventResponse, MonthlyMetricsResponse


router = APIRouter(prefix="/observer", tags=["observer"])


# Response schemas согласно D-19
class AnomalyItem(BaseModel):
    """Элемент списка аномалий"""
    category: str
    current_val: float
    baseline_val: float
    delta_pct: float
    status: str
    detected_at: str


class AnomaliesResponse(BaseModel):
    """Response для GET /anomalies"""
    month_key: str
    anomalies: List[AnomalyItem]
    detection_status: str  # "ok" | "insufficient_history" | "skip_mode" | "pending"


class TrendItem(BaseModel):
    """Элемент списка трендов"""
    month_key: str
    burn_rate: float
    savings_rate: float
    total_spent: float
    total_income: float
    currency: str
    rate_type: str  # "manual" | "skip"


class TrendsResponse(BaseModel):
    """Response для GET /trends"""
    period: List[str]  # ASC сортировка, всегда
    metrics: List[TrendItem]


def get_last_full_month() -> str:
    """Возвращает month_key последнего полного месяца (предыдущий месяц)"""
    # D-22: используем relativedelta для точного вычисления предыдущего месяца
    # Первое число текущего месяца минус один месяц = последний день предыдущего месяца
    last_month = date.today().replace(day=1) - relativedelta(months=1)
    return last_month.strftime("%Y-%m")


@router.get("/anomalies", response_model=AnomaliesResponse)
async def get_anomalies(
    month_key: Optional[str] = Query(None, description="Месяц в формате YYYY-MM, по умолчанию последний полный месяц"),
    status: Optional[str] = Query("new", description="Статус аномалий: 'new', 'notified', 'dismissed'"),
    db: Session = Depends(get_db)
) -> AnomaliesResponse:
    """
    Возвращает список аномалий за указанный месяц.
    
    detection_status:
    - "ok": история достаточна (≥3 месяцев данных)
    - "insufficient_history": история <3 месяцев
    - "skip_mode": месяц с rate_type='skip' (конвертация отключена)
    - "pending": observer ещё не завершил scan для этого месяца (нет anomaly_events)
    """
    # Определяем month_key если не указан
    if month_key is None:
        month_key = get_last_full_month()
    
    logger.info(f"GET /anomalies for month_key={month_key}, status={status}")
    
    # Проверяем существование monthly_metrics для этого месяца
    monthly_metric = db.execute(
        text("SELECT rate_type, updated_at FROM monthly_metrics WHERE month_key = :month_key"),
        {"month_key": month_key}
    ).fetchone()
    
    # Если месяц с rate_type='skip', возвращаем skip_mode
    if monthly_metric and monthly_metric[0] == "skip":
        return AnomaliesResponse(
            month_key=month_key,
            anomalies=[],
            detection_status="skip_mode"
        )
    
    # Проверяем, завершён ли scan (есть ли anomaly_events для этого месяца)
    anomaly_check = db.execute(
        text("SELECT COUNT(*) FROM anomaly_events WHERE month_key = :month_key"),
        {"month_key": month_key}
    ).fetchone()
    
    has_anomalies = anomaly_check[0] > 0 if anomaly_check else False
    
    # Если нет anomaly_events, статус pending (observer ещё не завершил scan)
    if not has_anomalies:
        return AnomaliesResponse(
            month_key=month_key,
            anomalies=[],
            detection_status="pending"
        )
    
    # Проверяем достаточность истории (D-17)
    # Нужно проверить, есть ли данные за 3 предыдущих месяца
    year, month = map(int, month_key.split('-'))
    prev_months = []
    for i in range(1, 4):  # 3 предыдущих месяца
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1
        prev_months.append(f"{y:04d}-{m:02d}")
    
    # Проверяем наличие данных за все 3 предыдущих месяца
    prev_months_str = ", ".join([f"'{m}'" for m in prev_months])
    history_check = db.execute(
        text(f"""
            SELECT COUNT(DISTINCT month_key) as month_count
            FROM monthly_metrics 
            WHERE month_key IN ({prev_months_str}) AND rate_type != 'skip'
        """)
    ).fetchone()
    
    month_count = history_check[0] if history_check else 0
    detection_status = "ok" if month_count >= 3 else "insufficient_history"
    
    # Получаем аномалии
    query = text("""
        SELECT category, current_val, baseline_val, delta_pct, status, detected_at
        FROM anomaly_events 
        WHERE month_key = :month_key AND status = :status
        ORDER BY delta_pct DESC
    """)
    
    anomalies_rows = db.execute(query, {"month_key": month_key, "status": status}).fetchall()
    
    anomalies = []
    for row in anomalies_rows:
        anomalies.append(AnomalyItem(
            category=row[0],
            current_val=float(row[1]),
            baseline_val=float(row[2]),
            delta_pct=float(row[3]),
            status=row[4],
            detected_at=row[5]
        ))
    
    return AnomaliesResponse(
        month_key=month_key,
        anomalies=anomalies,
        detection_status=detection_status
    )


@router.get("/trends", response_model=TrendsResponse)
async def get_trends(
    months: int = Query(3, ge=1, le=12, description="Количество месяцев для анализа (1-12)"),
    db: Session = Depends(get_db)
) -> TrendsResponse:
    """
    Возвращает метрики за указанное количество последних месяцев.
    
    Сортировка всегда ASC по month_key.
    Месяцы с rate_type='skip' включаются, но клиент видит несовместимые периоды явно.
    """
    logger.info(f"GET /trends for last {months} months")
    
    # Получаем последние N месяцев с данными
    query = text("""
        SELECT month_key, total_spent, total_income, savings_rate, burn_rate, 
               currency, fx_rate, rate_type, tx_count, updated_at
        FROM monthly_metrics 
        WHERE rate_type != 'skip'  -- исключаем skip режим для сопоставимости
        ORDER BY month_key DESC
        LIMIT :limit
    """)
    
    metrics_rows = db.execute(query, {"limit": months}).fetchall()
    
    # Сортируем ASC для response (как требуется в D-19)
    metrics_rows_sorted = sorted(metrics_rows, key=lambda x: x[0])
    
    period = []
    metrics = []
    
    for row in metrics_rows_sorted:
        month_key = row[0]
        period.append(month_key)
        
        metrics.append(TrendItem(
            month_key=month_key,
            burn_rate=float(row[4]),  # burn_rate
            savings_rate=float(row[3]),  # savings_rate
            total_spent=float(row[1]),  # total_spent
            total_income=float(row[2]),  # total_income
            currency=row[5],
            rate_type=row[7]
        ))
    
    # Если нет данных, возвращаем пустые списки
    if not period:
        # Пробуем получить любые данные (включая skip) для демонстрации
        fallback_query = text("""
            SELECT month_key, total_spent, total_income, savings_rate, burn_rate, 
                   currency, fx_rate, rate_type
            FROM monthly_metrics 
            ORDER BY month_key DESC
            LIMIT :limit
        """)
        fallback_rows = db.execute(fallback_query, {"limit": months}).fetchall()
        fallback_rows_sorted = sorted(fallback_rows, key=lambda x: x[0])
        
        for row in fallback_rows_sorted:
            month_key = row[0]
            period.append(month_key)
            
            metrics.append(TrendItem(
                month_key=month_key,
                burn_rate=float(row[4]),
                savings_rate=float(row[3]),
                total_spent=float(row[1]),
                total_income=float(row[2]),
                currency=row[5],
                rate_type=row[7]
            ))
    
    return TrendsResponse(
        period=period,
        metrics=metrics
    )