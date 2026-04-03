from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from loguru import logger

from core.database import get_db
from etl.parser import parse_csv
from etl.loader import load_transactions, LoadResult

router = APIRouter(prefix="/ingest", tags=["ingest"])


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
            return LoadResult(inserted=0, skipped_duplicates=0, errors=0)
        
        # Загружаем в БД
        result = load_transactions(rows, db, source_file=file.filename)
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing CSV {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")