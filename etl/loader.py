from datetime import datetime
from decimal import Decimal
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from loguru import logger
from pydantic import BaseModel

from core.models import Transaction, UploadSession
from etl.parser import TransactionRaw, load_accounts_mapping


class LoadResult(BaseModel):
    """Результат загрузки транзакций"""
    inserted: int = 0
    skipped_duplicates: int = 0
    skipped_technical: int = 0  # НОВОЕ ПОЛЕ
    errors: int = 0
    detection_status: str = "pending"  # 'pending' | 'running' | 'completed' | 'error' | 'skip_mode'


def load_transactions(rows: List[TransactionRaw], db: Session, source_file: str = "unknown.csv", fx_rate: float = 0.0, rate_type: str = "skip") -> LoadResult:
    """
    Загружает транзакции в БД.
    
    Использует INSERT OR IGNORE по уникальному constraint.
    """
    result = LoadResult()
    
    if not rows:
        logger.warning("No rows to load")
        return result
    
    # Загружаем маппинг аккаунтов на валюты
    accounts_mapping = load_accounts_mapping()
    
    for row in rows:
        with db.begin_nested():
            try:
                # Определяем валюту на основе маппинга accounts.yml
                currency = row.currency
                if row.account:
                    # Ищем точное совпадение
                    if row.account in accounts_mapping:
                        currency = accounts_mapping[row.account]
                    else:
                        # Ищем по wildcard (например, "Bybit*")
                        for pattern, mapped_currency in accounts_mapping.items():
                            if "*" in pattern:
                                prefix = pattern.replace("*", "")
                                if row.account.startswith(prefix):
                                    currency = mapped_currency
                                    break
                        else:
                            # Если account не найден в маппинге
                            currency = "UNKNOWN"
                            logger.warning(f"Account '{row.account}' not found in accounts mapping, currency set to UNKNOWN")
                else:
                    # Если account отсутствует
                    currency = "UNKNOWN"
                    logger.warning(f"Transaction has no account, currency set to UNKNOWN")
                
                # Создаём объект Transaction из TransactionRaw
                transaction = Transaction(
                    date=row.date.date(),  # храним только дату без времени
                    description=row.description,
                    amount=Decimal(str(row.amount)),
                    currency=currency,
                    category=row.category,
                    account=row.account,
                    source_file=source_file,
                    created_at=datetime.utcnow()
                )
                
                db.add(transaction)
                db.flush()  # Проверяем constraint без коммита
                result.inserted += 1
                
            except IntegrityError:
                # Дубликат по уникальному constraint - nested transaction автоматически откатывается
                result.skipped_duplicates += 1
                logger.debug(f"Duplicate transaction skipped: {row.date} {row.amount} {row.account} {row.description}")
                
            except Exception as e:
                result.errors += 1
                logger.error(f"Error loading transaction {row}: {e}")
    
    # Сохраняем метаданные загрузки если транзакции были успешно загружены
    if result.inserted > 0:
        try:
            # Вычисляем min_date и max_date из загруженных транзакций
            dates = [row.date.date() for row in rows]
            min_date = min(dates)
            max_date = max(dates)
            
            upload_session = UploadSession(
                min_date=min_date,
                max_date=max_date,
                transactions_count=result.inserted,
                fx_rate=fx_rate,
                rate_type=rate_type,
                uploaded_at=datetime.utcnow()
            )
            db.add(upload_session)
            db.commit()
            logger.info(f"Upload session saved: {min_date} to {max_date}, {result.inserted} transactions, fx_rate={fx_rate}, rate_type={rate_type}")
            
        except Exception as e:
            logger.error(f"Failed to save upload session: {e}")
            # Не прерываем процесс, только логируем ошибку
    
    try:
        db.commit()
        logger.info(f"Load result: {result.inserted} inserted, {result.skipped_duplicates} duplicates skipped, {result.errors} errors")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to commit transactions: {e}")
        result.errors += len(rows)  # Все строки не загружены
    
    return result