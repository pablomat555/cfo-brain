import csv
import io
from datetime import datetime
from decimal import Decimal
from typing import List
from pathlib import Path

import yaml
from dateutil import parser as date_parser
from loguru import logger
from pydantic import BaseModel, Field


class TransactionRaw(BaseModel):
    """Сырые данные транзакции из CSV"""
    date: datetime
    description: str
    amount: float
    currency: str = "UAH"
    account: str | None = None
    category: str | None = None
    is_transfer: bool = False


def load_accounts_mapping() -> dict[str, str]:
    """Загружает маппинг аккаунтов на валюты из accounts.yml"""
    try:
        with open("accounts.yml", "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("accounts", {})
    except FileNotFoundError:
        logger.warning("accounts.yml not found, using empty mapping")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse accounts.yml: {e}")
        return {}


def load_parser_types() -> dict[str, str]:
    """Загружает маппинг аккаунтов на тип парсера из accounts.yml"""
    try:
        with open("accounts.yml", "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("parser_types", {})
    except FileNotFoundError:
        logger.warning("accounts.yml not found, using empty parser mapping")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse accounts.yml: {e}")
        return {}


def parse_csv(file_bytes: bytes, filename: str) -> List[TransactionRaw]:
    """
    Парсит CSV файл в список TransactionRaw.
    
    Колонки (точные имена из CSV):
    Date, Description, Category, Payee, Tag, Account, Transfer Account, Amount
    """
    accounts_mapping = load_accounts_mapping()
    parser_types = load_parser_types()
    logger.debug(f"Loaded parser types: {parser_types}")
    results = []
    
    # Пробуем разные кодировки
    encodings = ["utf-8", "cp1251", "latin-1"]
    content = None
    
    for encoding in encodings:
        try:
            content = file_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    
    if content is None:
        logger.error(f"Failed to decode CSV file {filename}")
        return []
    
    # Определяем разделитель
    sample = content[:1024]
    delimiter = ";" if ";" in sample else ","
    
    # Парсим CSV
    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
    
    required_columns = {"Date", "Amount", "Account"}
    if not required_columns.issubset(reader.fieldnames or []):
        logger.error(f"CSV missing required columns. Found: {reader.fieldnames}")
        return []
    
    for i, row in enumerate(reader, start=1):
        try:
            # Парсим дату
            date_str = row.get("Date", "").strip()
            if not date_str:
                logger.warning(f"Row {i}: empty date, skipping")
                continue
                
            try:
                date = date_parser.parse(date_str)
            except Exception as e:
                logger.warning(f"Row {i}: failed to parse date '{date_str}': {e}")
                continue
            
            # Парсим amount
            amount_str = row.get("Amount", "").strip()
            if not amount_str:
                logger.warning(f"Row {i}: empty amount, skipping")
                continue
            
            # Очищаем amount: убираем неразрывный пробел (\u00A0), обычные пробелы, заменяем запятую на точку
            amount_str = amount_str.replace("\u00a0", "").replace(" ", "").replace(",", ".")
            try:
                amount = float(amount_str)
            except ValueError:
                logger.warning(f"Row {i}: invalid amount '{amount_str}', skipping")
                continue
            
            # Определяем account
            account = row.get("Account", "").strip() or None
            
            # Определяем currency по account из маппинга
            currency = "UAH"  # default
            if account and account in accounts_mapping:
                currency = accounts_mapping[account]
            elif account:
                logger.warning(f"Account '{account}' not found in accounts mapping, using 'UNKNOWN'")
                currency = "UNKNOWN"
            
            # Проверяем перевод
            transfer_account = row.get("Transfer Account", "").strip()
            is_transfer = bool(transfer_account)
            
            # Если это перевод, не грузим в transactions
            if is_transfer:
                logger.info(f"Row {i}: transfer transaction (from {account} to {transfer_account}), skipping")
                continue
            
            # Description из Payee или Description
            description = row.get("Payee", "").strip() or row.get("Description", "").strip()
            category = row.get("Category", "").strip() or None
            
            # Пропускаем технические записи Balancing transaction
            if category == "Balancing transaction":
                logger.info(f"Row {i}: Balancing transaction, skipping")
                continue
            
            results.append(TransactionRaw(
                date=date,
                description=description,
                amount=amount,
                currency=currency,
                account=account,
                category=category,
                is_transfer=is_transfer
            ))
            
        except Exception as e:
            logger.error(f"Row {i}: error processing row: {e}")
            continue
    
    logger.info(f"Parsed {len(results)} transactions from {filename}")
    return results