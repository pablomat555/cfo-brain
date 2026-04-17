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
    CapitalSnapshotIngestResponse, PortfolioPositionCreate, PortfolioPositionResponse,
    PortfolioPositionListResponse, AccountUpdateRequest
)
from etl.capital_parser import parse_capital_snapshot_csv
from core.capital_classifier import classify_asset

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
        if account.fx_rate != 0:
            balance_usd = account.balance / account.fx_rate
        else:
            balance_usd = 0.0
        
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


@router.patch("/account/{account_id}", response_model=AccountBalanceResponse)
def update_account_balance(
    account_id: int,
    update_data: AccountUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Частичное обновление счёта по ID.
    """
    try:
        # Находим запись
        account = db.query(AccountBalance).filter(AccountBalance.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Нормализация fx_rate для USD/USDT
        if update_data.currency in ("USD", "USDT"):
            update_data.fx_rate = 1.0
        elif update_data.currency is not None and update_data.fx_rate is None:
            # Для других валют fx_rate должен быть указан (валидатор уже проверил)
            pass
        
        # Partial update: обновляем только non-None поля
        if update_data.balance is not None:
            account.balance = update_data.balance
        if update_data.currency is not None:
            account.currency = update_data.currency
        if update_data.fx_rate is not None:
            account.fx_rate = update_data.fx_rate
        if update_data.bucket is not None:
            account.bucket = update_data.bucket
        
        account.updated_at = datetime.utcnow()
        
        try:
            db.commit()
            db.refresh(account)
        except Exception as e:
            # IntegrityError (например, нарушение уникальности)
            db.rollback()
            raise HTTPException(status_code=409, detail=f"Conflict: {str(e)}")
        
        # Вычисляем balance_usd для ответа
        if account.fx_rate != 0:
            balance_usd = account.balance / account.fx_rate
        else:
            balance_usd = 0.0
        
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating account balance: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.post("/position", response_model=PortfolioPositionResponse)
def upsert_portfolio_position(
    position_data: PortfolioPositionCreate,
    db: Session = Depends(get_db)
):
    """
    Upsert позиции портфеля (создание или обновление по account_name, asset_symbol, as_of_date)
    """
    try:
        # Преобразуем строку даты в объект date
        as_of_date = datetime.strptime(position_data.as_of_date, "%Y-%m-%d").date()
        
        # Классифицируем актив
        asset_type, liquidity_bucket = classify_asset(position_data.asset_symbol)
        
        # Проверяем существующую запись
        existing = db.query(PortfolioPosition).filter(
            PortfolioPosition.account_name == position_data.account_name,
            PortfolioPosition.asset_symbol == position_data.asset_symbol,
            PortfolioPosition.as_of_date == as_of_date
        ).first()
        
        if existing:
            # Обновляем существующую запись
            existing.quantity = position_data.quantity
            existing.market_value = position_data.market_value
            existing.currency = position_data.currency
            existing.fx_rate = position_data.fx_rate
            existing.asset_type = asset_type
            existing.liquidity_bucket = liquidity_bucket
            existing.source = position_data.source
            db.commit()
            db.refresh(existing)
            logger.info(f"Updated portfolio position: {position_data.account_name} {position_data.asset_symbol} for {as_of_date}")
            position = existing
        else:
            # Создаём новую запись
            position = PortfolioPosition(
                account_name=position_data.account_name,
                asset_symbol=position_data.asset_symbol,
                quantity=position_data.quantity,
                market_value=position_data.market_value,
                currency=position_data.currency,
                fx_rate=position_data.fx_rate,
                asset_type=asset_type,
                liquidity_bucket=liquidity_bucket,
                as_of_date=as_of_date,
                source=position_data.source
            )
            db.add(position)
            db.commit()
            db.refresh(position)
            logger.info(f"Created new portfolio position: {position_data.account_name} {position_data.asset_symbol} for {as_of_date}")
        
        # Вычисляем market_value_usd для ответа
        if position.fx_rate != 0:
            market_value_usd = position.market_value / position.fx_rate
        else:
            market_value_usd = 0.0
        
        return PortfolioPositionResponse(
            id=position.id,
            account_name=position.account_name,
            asset_symbol=position.asset_symbol,
            asset_type=position.asset_type,
            quantity=position.quantity,
            market_value=position.market_value,
            currency=position.currency,
            fx_rate=position.fx_rate,
            liquidity_bucket=position.liquidity_bucket,
            as_of_date=position.as_of_date.isoformat(),
            source=position.source,
            created_at=position.created_at.isoformat(),
            market_value_usd=market_value_usd
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error upserting portfolio position: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.get("/state", response_model=CapitalStateResponse)
def get_capital_state(
    as_of_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Получить состояние капитала на указанную дату (или последнюю доступную)
    с учётом Single Source Rule (D-30) и breakdown по asset_type и liquidity_bucket.
    """
    try:
        # Определяем целевую дату
        target_date = None
        if as_of_date:
            target_date = datetime.strptime(as_of_date, "%Y-%m-%d").date()
        else:
            # Берём максимальную доступную дату из обеих таблиц
            max_date_balance = db.query(func.max(AccountBalance.as_of_date)).scalar()
            max_date_position = db.query(func.max(PortfolioPosition.as_of_date)).scalar()
            max_date = max(max_date_balance or date.min, max_date_position or date.min)
            if max_date == date.min:
                raise HTTPException(status_code=404, detail="No capital snapshot data available")
            target_date = max_date
        
        # Получаем все балансы и позиции на целевую дату
        balances = db.query(AccountBalance).filter(
            AccountBalance.as_of_date == target_date
        ).all()
        positions = db.query(PortfolioPosition).filter(
            PortfolioPosition.as_of_date == target_date
        ).all()
        
        if not balances and not positions:
            raise HTTPException(
                status_code=404,
                detail=f"No capital snapshot data for date {target_date}"
            )
        
        # Single Source Rule: собираем account_name, которые имеют позиции
        accounts_with_positions = {pos.account_name for pos in positions}
        
        # Инициализация структур
        by_bucket: Dict[str, Dict[str, Any]] = {
            "liquid": {"total_usd": 0.0, "accounts": []},
            "semi_liquid": {"total_usd": 0.0, "accounts": []},
            "investment": {"total_usd": 0.0, "accounts": []},
            "illiquid": {"total_usd": 0.0, "accounts": []}
        }
        
        # Возможные значения asset_type из классификатора
        by_asset_type: Dict[str, Dict[str, Any]] = {
            "stablecoin": {"total_usd": 0.0, "positions": []},
            "crypto": {"total_usd": 0.0, "positions": []},
            "bond_etf": {"total_usd": 0.0, "positions": []},
            "etf": {"total_usd": 0.0, "positions": []},
            "alternative": {"total_usd": 0.0, "positions": []},
            "receivable": {"total_usd": 0.0, "positions": []},
            "cash": {"total_usd": 0.0, "positions": []}
        }
        
        by_liquidity_bucket: Dict[str, Dict[str, Any]] = {
            "liquid": {"total_usd": 0.0, "positions": []},
            "semi_liquid": {"total_usd": 0.0, "positions": []},
            "investment": {"total_usd": 0.0, "positions": []},
            "illiquid": {"total_usd": 0.0, "positions": []}
        }
        
        total_net_worth_usd = 0.0
        
        # Обрабатываем позиции (приоритет)
        for pos in positions:
            if pos.fx_rate != 0:
                value_usd = pos.market_value / pos.fx_rate
            else:
                value_usd = 0.0
            
            total_net_worth_usd += value_usd
            
            # by_bucket (liquidity_bucket)
            bucket = pos.liquidity_bucket
            if bucket not in by_bucket:
                bucket = "liquid"  # fallback
            by_bucket[bucket]["total_usd"] += value_usd
            by_bucket[bucket]["accounts"].append({
                "account_name": pos.account_name,
                "asset_symbol": pos.asset_symbol,
                "market_value": pos.market_value,
                "currency": pos.currency,
                "fx_rate": pos.fx_rate,
                "value_usd": value_usd
            })
            
            # by_asset_type
            asset_type = pos.asset_type
            if asset_type not in by_asset_type:
                asset_type = "crypto"  # fallback
            by_asset_type[asset_type]["total_usd"] += value_usd
            by_asset_type[asset_type]["positions"].append({
                "account_name": pos.account_name,
                "asset_symbol": pos.asset_symbol,
                "market_value": pos.market_value,
                "currency": pos.currency,
                "value_usd": value_usd
            })
            
            # by_liquidity_bucket (дублирует by_bucket, но для consistency)
            by_liquidity_bucket[bucket]["total_usd"] += value_usd
            by_liquidity_bucket[bucket]["positions"].append({
                "account_name": pos.account_name,
                "asset_symbol": pos.asset_symbol,
                "market_value": pos.market_value,
                "currency": pos.currency,
                "value_usd": value_usd
            })
        
        # Обрабатываем балансы, исключая аккаунты с позициями
        for balance in balances:
            if balance.account_name in accounts_with_positions:
                continue  # пропускаем, т.к. уже учтены в позициях
            
            if balance.fx_rate != 0:
                balance_usd = balance.balance / balance.fx_rate
            else:
                balance_usd = 0.0
            
            total_net_worth_usd += balance_usd
            
            bucket = balance.bucket
            if bucket not in by_bucket:
                bucket = "liquid"
            by_bucket[bucket]["total_usd"] += balance_usd
            by_bucket[bucket]["accounts"].append({
                "account_name": balance.account_name,
                "balance": balance.balance,
                "currency": balance.currency,
                "fx_rate": balance.fx_rate,
                "balance_usd": balance_usd
            })
            
            # Для балансов asset_type = "cash" (предположительно)
            asset_type = "cash"
            by_asset_type[asset_type]["total_usd"] += balance_usd
            by_asset_type[asset_type]["positions"].append({
                "account_name": balance.account_name,
                "asset_symbol": "CASH",
                "market_value": balance.balance,
                "currency": balance.currency,
                "value_usd": balance_usd
            })
            
            # liquidity_bucket = bucket
            by_liquidity_bucket[bucket]["total_usd"] += balance_usd
            by_liquidity_bucket[bucket]["positions"].append({
                "account_name": balance.account_name,
                "asset_symbol": "CASH",
                "market_value": balance.balance,
                "currency": balance.currency,
                "value_usd": balance_usd
            })
        
        # Удаляем пустые категории
        by_bucket = {k: v for k, v in by_bucket.items() if v["total_usd"] > 0 or v["accounts"]}
        by_asset_type = {k: v for k, v in by_asset_type.items() if v["total_usd"] > 0 or v["positions"]}
        by_liquidity_bucket = {k: v for k, v in by_liquidity_bucket.items() if v["total_usd"] > 0 or v["positions"]}
        
        return CapitalStateResponse(
            as_of_date=target_date.isoformat(),
            total_net_worth_usd=total_net_worth_usd,
            by_bucket=by_bucket,
            by_asset_type=by_asset_type,
            by_liquidity_bucket=by_liquidity_bucket
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


@router.get("/positions", response_model=PortfolioPositionListResponse)
def get_portfolio_positions(
    as_of_date: Optional[str] = None,
    account_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Получить список позиций портфеля с фильтрами по дате и счёту
    """
    try:
        query = db.query(PortfolioPosition)
        
        if as_of_date:
            target_date = datetime.strptime(as_of_date, "%Y-%m-%d").date()
            query = query.filter(PortfolioPosition.as_of_date == target_date)
        
        if account_name:
            query = query.filter(PortfolioPosition.account_name == account_name)
        
        # Сортируем по дате (новые сверху) и по счёту
        positions = query.order_by(
            PortfolioPosition.as_of_date.desc(),
            PortfolioPosition.account_name,
            PortfolioPosition.asset_symbol
        ).all()
        
        # Преобразуем в response
        position_responses = []
        for pos in positions:
            if pos.fx_rate != 0:
                market_value_usd = pos.market_value / pos.fx_rate
            else:
                market_value_usd = 0.0
            
            position_responses.append(
                PortfolioPositionResponse(
                    id=pos.id,
                    account_name=pos.account_name,
                    asset_symbol=pos.asset_symbol,
                    asset_type=pos.asset_type,
                    quantity=pos.quantity,
                    market_value=pos.market_value,
                    currency=pos.currency,
                    fx_rate=pos.fx_rate,
                    liquidity_bucket=pos.liquidity_bucket,
                    as_of_date=pos.as_of_date.isoformat(),
                    source=pos.source,
                    created_at=pos.created_at.isoformat(),
                    market_value_usd=market_value_usd
                )
            )
        
        return PortfolioPositionListResponse(positions=position_responses)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error getting portfolio positions: {e}")
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
            # Обрабатываем portfolio positions
            for row in parsed_data:
                try:
                    # Проверяем обязательные поля
                    if not all(k in row for k in ['account_name', 'asset_symbol', 'quantity', 'market_value', 'currency', 'as_of_date']):
                        logger.warning(f"Skipping row with missing fields: {row}")
                        continue
                    
                    # Преобразуем дату
                    row_date = datetime.strptime(row['as_of_date'], "%Y-%m-%d").date()
                    if as_of_date is None:
                        as_of_date = row_date
                    
                    # Классифицируем актив
                    asset_type, liquidity_bucket = classify_asset(row['asset_symbol'])
                    
                    # Проверяем существующую запись
                    existing = db.query(PortfolioPosition).filter(
                        PortfolioPosition.account_name == row['account_name'],
                        PortfolioPosition.asset_symbol == row['asset_symbol'],
                        PortfolioPosition.as_of_date == row_date
                    ).first()
                    
                    if existing:
                        # Обновляем
                        existing.quantity = float(row['quantity'])
                        existing.market_value = float(row['market_value'])
                        existing.currency = row['currency']
                        existing.fx_rate = float(row.get('fx_rate', 1.0))
                        existing.asset_type = asset_type
                        existing.liquidity_bucket = liquidity_bucket
                        existing.source = row.get('source', 'csv')
                    else:
                        # Создаём новую
                        position = PortfolioPosition(
                            account_name=row['account_name'],
                            asset_symbol=row['asset_symbol'],
                            quantity=float(row['quantity']),
                            market_value=float(row['market_value']),
                            currency=row['currency'],
                            fx_rate=float(row.get('fx_rate', 1.0)),
                            asset_type=asset_type,
                            liquidity_bucket=liquidity_bucket,
                            as_of_date=row_date,
                            source=row.get('source', 'csv')
                        )
                        db.add(position)
                    
                    accounts.add(row['account_name'])
                    rows_loaded += 1
                    
                except (ValueError, KeyError) as e:
                    logger.warning(f"Error parsing row {row}: {e}")
                    continue
            
            db.commit()
        
        return CapitalSnapshotIngestResponse(
            rows_loaded=rows_loaded,
            snapshot_type=snapshot_type,
            as_of_date=as_of_date.isoformat() if as_of_date else "",
            accounts=list(accounts)
        )
        
    except Exception as e:
        logger.error(f"Error ingesting capital snapshot: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")