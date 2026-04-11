from datetime import datetime, date
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from loguru import logger

from core.database import get_db
from core.models import (
    AccountBalance, PortfolioPosition, AccountBalanceCreate, 
    AccountBalanceResponse, CapitalStateResponse, AccountListResponse,
    CapitalSnapshotIngestResponse
)
from etl.capital_parser import parse_capital_snapshot_csv

router = APIRouter(prefix="/capital", tags=["capital"])


@router.post("/account", response_model=AccountBalanceResponse)
def upsert_account_balance(
    account_data: AccountBalanceCreate,
    db: Session = Depends(get_db)
):
    """
    Upsert баланса счёта (создание или обновление по account_name и as_of_date)
    """
    try:
        # Преобразуем строку даты в объект date
        as_of_date = datetime.strptime(account_data.as_of_date, "%Y-%m-%d").date()
        
        # Проверяем существующую запись
        existing = db.query(AccountBalance).filter(
            AccountBalance.account_name == account_data.account_name,
            AccountBalance.as_of_date == as_of_date
        ).first()
        
        if existing:
            # Обновляем существующую запись
            existing.balance = account_data.balance
            existing.currency = account_data.currency
            existing.fx_rate = account_data.fx_rate
            existing.bucket = account_data.bucket
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            logger.info(f"Updated account balance: {account_data.account_name} for {as_of_date}")
            account = existing
        else:
            # Создаём новую запись
            account = AccountBalance(
                account_name=account_data.account_name,
                balance=account_data.balance,
                currency=account_data.currency,
                fx_rate=account_data.fx_rate,
                bucket=account_data.bucket,
                as_of_date=as_of_date,
                source="manual"
            )
            db.add(account)
            db.commit()
            db.refresh(account)
            logger.info(f"Created new account balance: {account_data.account_name} for {as_of_date}")
        
        # Вычисляем balance_usd для ответа
        balance_usd = account.balance * account.fx_rate
        
        return AccountBalanceResponse(
            id=account.id,
            account_name=account.account_name,
            balance=account.balance,
            currency=account.currency,
            fx_rate=account.fx_rate,
            bucket=account.bucket,
            as_of_date=account.as_of_date.isoformat(),
            source=account.source,
            created_at=account.created_at.isoformat(),
            updated_at=account.updated_at.isoformat(),
            balance_usd=balance_usd
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error upserting account balance: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.get("/state", response_model=CapitalStateResponse)
def get_capital_state(
    as_of_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Получить состояние капитала на указанную дату (или последнюю доступную)
    """
    try:
        # Определяем целевую дату
        target_date = None
        if as_of_date:
            target_date = datetime.strptime(as_of_date, "%Y-%m-%d").date()
        else:
            # Берём максимальную доступную дату
            max_date_result = db.query(func.max(AccountBalance.as_of_date)).scalar()
            if not max_date_result:
                raise HTTPException(status_code=404, detail="No capital snapshot data available")
            target_date = max_date_result
        
        # Получаем все балансы на целевую дату
        balances = db.query(AccountBalance).filter(
            AccountBalance.as_of_date == target_date
        ).all()
        
        if not balances:
            raise HTTPException(
                status_code=404, 
                detail=f"No capital snapshot data for date {target_date}"
            )
        
        # Группируем по bucket и вычисляем totals
        by_bucket: Dict[str, Dict[str, Any]] = {
            "liquid": {"total_usd": 0.0, "accounts": []},
            "semi_liquid": {"total_usd": 0.0, "accounts": []},
            "investment": {"total_usd": 0.0, "accounts": []}
        }
        
        total_net_worth_usd = 0.0
        
        for balance in balances:
            bucket = balance.bucket
            if bucket not in by_bucket:
                continue
                
            balance_usd = balance.balance * balance.fx_rate
            total_net_worth_usd += balance_usd
            by_bucket[bucket]["total_usd"] += balance_usd
            
            account_info = {
                "account_name": balance.account_name,
                "balance": balance.balance,
                "currency": balance.currency,
                "fx_rate": balance.fx_rate,
                "balance_usd": balance_usd
            }
            by_bucket[bucket]["accounts"].append(account_info)
        
        return CapitalStateResponse(
            as_of_date=target_date.isoformat(),
            total_net_worth_usd=total_net_worth_usd,
            by_bucket=by_bucket
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting capital state: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.get("/accounts", response_model=AccountListResponse)
def get_accounts_list(db: Session = Depends(get_db)):
    """
    Получить список уникальных account_name из account_balances
    """
    try:
        accounts = db.query(AccountBalance.account_name).distinct().all()
        account_names = [acc[0] for acc in accounts]
        
        return AccountListResponse(accounts=account_names)
        
    except Exception as e:
        logger.error(f"Error getting accounts list: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.post("/ingest/capital_snapshot", response_model=CapitalSnapshotIngestResponse)
async def ingest_capital_snapshot(
    file: UploadFile = File(...),
    snapshot_type: str = Form(...),  # "account" или "portfolio"
    db: Session = Depends(get_db)
):
    """
    Загрузить CSV файл с капитальным снапшотом (account или portfolio)
    """
    if snapshot_type not in ["account", "portfolio"]:
        raise HTTPException(status_code=400, detail="snapshot_type must be 'account' or 'portfolio'")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        # Читаем содержимое файла
        content = await file.read()
        content_str = content.decode('utf-8')
        
        # Парсим CSV
        parsed_data = parse_capital_snapshot_csv(content_str, snapshot_type)
        
        if not parsed_data:
            raise HTTPException(status_code=400, detail="No valid data found in CSV")
        
        rows_loaded = 0
        accounts = set()
        as_of_date = None
        
        if snapshot_type == "account":
            # Обрабатываем account balances
            for row in parsed_data:
                try:
                    # Проверяем обязательные поля
                    if not all(k in row for k in ['account_name', 'balance', 'currency', 'bucket', 'as_of_date']):
                        logger.warning(f"Skipping row with missing fields: {row}")
                        continue
                    
                    # Преобразуем дату
                    row_date = datetime.strptime(row['as_of_date'], "%Y-%m-%d").date()
                    if as_of_date is None:
                        as_of_date = row_date
                    
                    # Проверяем существующую запись
                    existing = db.query(AccountBalance).filter(
                        AccountBalance.account_name == row['account_name'],
                        AccountBalance.as_of_date == row_date
                    ).first()
                    
                    if existing:
                        # Обновляем
                        existing.balance = float(row['balance'])
                        existing.currency = row['currency']
                        existing.fx_rate = float(row.get('fx_rate', 1.0))
                        existing.bucket = row['bucket']
                        existing.source = row.get('source', 'csv')
                        existing.updated_at = datetime.utcnow()
                    else:
                        # Создаём новую
                        account = AccountBalance(
                            account_name=row['account_name'],
                            balance=float(row['balance']),
                            currency=row['currency'],
                            fx_rate=float(row.get('fx_rate', 1.0)),
                            bucket=row['bucket'],
                            as_of_date=row_date,
                            source=row.get('source', 'csv')
                        )
                        db.add(account)
                    
                    accounts.add(row['account_name'])
                    rows_loaded += 1
                    
                except (ValueError, KeyError) as e:
                    logger.warning(f"Error parsing row {row}: {e}")
                    continue
            
            db.commit()
            
        else:
            # Для portfolio positions (структура создана, но данные будут в Task #1B)
            # Пока просто логируем
            logger.info(f"Received portfolio snapshot with {len(parsed_data)} rows (data loading in Task #1B)")
            rows_loaded = len(parsed_data)
            as_of_date = datetime.now().date() if not parsed_data else None
        
        return CapitalSnapshotIngestResponse(
            rows_loaded=rows_loaded,
            snapshot_type=snapshot_type,
            as_of_date=as_of_date.isoformat() if as_of_date else "",
            accounts=list(accounts)
        )
        
    except Exception as e:
        logger.error(f"Error ingesting capital snapshot: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")