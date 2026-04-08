import asyncio
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from loguru import logger

from core.database import get_db
from etl.parser import parse_csv
from etl.loader import load_transactions, LoadResult
from analytics.metrics_service import recalculate
from analytics.anomaly_service import scan

router = APIRouter(prefix="/ingest", tags=["ingest"])


async def _run_observer(min_date, max_date):
    """
    Асинхронно запускает Observer pipeline для пересчёта метрик и детекции аномалий.
    
    Args:
        min_date: минимальная дата в загруженных транзакциях
        max_date: максимальная дата в загруженных транзакциях
    """
    try:
        # Определяем месяцы, которые нужно пересчитать
        # Проходим по всем месяцам между min_date и max_date включительно
        months_to_process = set()
        
        current = min_date.replace(day=1)
        end = max_date.replace(day=1)
        
        while current <= end:
            month_key = current.strftime("%Y-%m")
            months_to_process.add(month_key)
            
            # Переходим к следующему месяцу
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        logger.info(f"Observer: processing months {sorted(months_to_process)}")
        
        for month_key in sorted(months_to_process):
            try:
                # Пересчитываем метрики
                recalculate(month_key)
                
                # Сканируем аномалии
                anomaly_count = scan(month_key)
                
                logger.info(f"Observer completed for {month_key}: {anomaly_count} anomalies")
                
            except Exception as e:
                logger.error(f"Observer error for {month_key}: {e}")
                # Продолжаем с другими месяцами
    
    except Exception as e:
        logger.error(f"Observer pipeline failed: {e}")


@router.post("/csv", response_model=LoadResult)
async def ingest_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
) -> LoadResult:
    """
    Принимает CSV файл, парсит и загружает транзакции в БД.
    
    Формат CSV: колонки Date, Description, Category, Payee, Tag, Account, Transfer Account, Amount
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    logger.info(f"Processing CSV upload: {file.filename}")
    
    try:
        # Читаем содержимое файла
        content = await file.read()
        
        # Парсим CSV
        rows = parse_csv(content, file.filename)
        if not rows:
            return LoadResult(inserted=0, skipped_duplicates=0, errors=0, detection_status="pending")
        
        # Загружаем в БД
        result = load_transactions(rows, db, source_file=file.filename)
        
        # Определяем min_date и max_date из загруженных транзакций
        if rows:
            dates = [row.date for row in rows]
            min_date = min(dates)
            max_date = max(dates)
            
            # Запускаем Observer асинхронно (не блокируем ответ)
            asyncio.create_task(_run_observer(min_date, max_date))
            logger.info(f"Observer task started for dates {min_date.date()} to {max_date.date()}")
        else:
            result.detection_status = "no_data"
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing CSV {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")