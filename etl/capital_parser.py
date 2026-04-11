import csv
import io
from typing import List, Dict, Any
from loguru import logger


def parse_capital_snapshot_csv(csv_content: str, snapshot_type: str) -> List[Dict[str, Any]]:
    """
    Парсит CSV файл капитального снапшота.
    
    Args:
        csv_content: Содержимое CSV файла как строка
        snapshot_type: "account" или "portfolio"
    
    Returns:
        Список словарей с распарсенными данными
    """
    if snapshot_type not in ["account", "portfolio"]:
        raise ValueError(f"Invalid snapshot_type: {snapshot_type}. Must be 'account' or 'portfolio'")
    
    try:
        # Читаем CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)
        
        if not rows:
            logger.warning("Empty CSV file")
            return []
        
        logger.info(f"Parsed {len(rows)} rows from capital snapshot CSV (type: {snapshot_type})")
        
        # Валидация и нормализация данных
        parsed_data = []
        
        for i, row in enumerate(rows, start=1):
            try:
                normalized_row = {}
                
                if snapshot_type == "account":
                    # Обрабатываем account snapshot
                    # Обязательные поля: account_name, balance, currency, bucket, as_of_date
                    required_fields = ["account_name", "balance", "currency", "bucket", "as_of_date"]
                    
                    for field in required_fields:
                        if field not in row:
                            raise ValueError(f"Missing required field: {field}")
                    
                    # Нормализуем значения
                    normalized_row["account_name"] = str(row["account_name"]).strip()
                    normalized_row["balance"] = float(row["balance"])
                    normalized_row["currency"] = str(row["currency"]).strip().upper()
                    normalized_row["bucket"] = str(row["bucket"]).strip().lower()
                    normalized_row["as_of_date"] = str(row["as_of_date"]).strip()
                    
                    # Опциональные поля
                    normalized_row["fx_rate"] = float(row.get("fx_rate", 1.0))
                    normalized_row["source"] = str(row.get("source", "csv")).strip().lower()
                    
                    # Валидация bucket
                    valid_buckets = ["liquid", "semi_liquid", "investment"]
                    if normalized_row["bucket"] not in valid_buckets:
                        logger.warning(f"Row {i}: Invalid bucket '{normalized_row['bucket']}', defaulting to 'liquid'")
                        normalized_row["bucket"] = "liquid"
                    
                else:
                    # Обрабатываем portfolio snapshot (структура для Task #1B)
                    # Пока просто сохраняем все поля
                    for key, value in row.items():
                        if value:
                            normalized_row[key.strip()] = value.strip()
                
                parsed_data.append(normalized_row)
                
            except (ValueError, KeyError) as e:
                logger.warning(f"Error parsing row {i}: {e}. Row data: {row}")
                continue
        
        logger.info(f"Successfully parsed {len(parsed_data)} valid rows")
        return parsed_data
        
    except csv.Error as e:
        logger.error(f"CSV parsing error: {e}")
        raise ValueError(f"Invalid CSV format: {e}")
    except Exception as e:
        logger.error(f"Unexpected error parsing capital snapshot CSV: {e}")
        raise


def validate_account_snapshot_row(row: Dict[str, Any]) -> bool:
    """
    Валидирует строку account snapshot.
    
    Returns:
        True если строка валидна
    """
    try:
        # Проверяем обязательные поля
        required = ["account_name", "balance", "currency", "bucket", "as_of_date"]
        for field in required:
            if field not in row:
                return False
        
        # Проверяем типы
        float(row["balance"])  # Должно быть числом
        str(row["currency"])
        str(row["bucket"])
        str(row["as_of_date"])  # Формат даты проверим позже
        
        # Проверяем bucket
        if row["bucket"] not in ["liquid", "semi_liquid", "investment"]:
            return False
            
        return True
        
    except (ValueError, TypeError):
        return False