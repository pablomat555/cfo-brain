from datetime import datetime, date
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from loguru import logger

from core.database import SessionLocal


def scan(month_key: str) -> int:
    """
    Сканирует категории за указанный месяц на наличие аномалий.
    
    Алгоритм:
    1. Для каждой категории в category_metrics за month_key
    2. Вычисляет baseline как среднее за 3 предыдущих полных месяца
    3. Применяет guards (baseline > 0, baseline > $10, достаточная история)
    4. Если delta_pct > threshold (50%), создаёт запись в anomaly_events
    
    Args:
        month_key: Строка в формате 'YYYY-MM'
    
    Returns:
        Количество обнаруженных аномалий
    
    Raises:
        Exception: В случае ошибки БД
    """
    db = SessionLocal()
    try:
        # Парсим month_key для вычисления предыдущих месяцев
        year, month = map(int, month_key.split('-'))
        
        # Получаем список последних 3 месяцев перед анализируемым
        prev_months = []
        for i in range(1, 4):  # 3 предыдущих месяца
            m = month - i
            y = year
            while m <= 0:
                m += 12
                y -= 1
            prev_months.append(f"{y:04d}-{m:02d}")
        
        # Проверяем, есть ли данные за все 3 предыдущих месяца
        prev_months_str = ", ".join([f"'{m}'" for m in prev_months])
        
        # Получаем категории за анализируемый месяц
        current_categories = db.execute(
            text("""
                SELECT category, total 
                FROM category_metrics 
                WHERE month_key = :month_key
                ORDER BY category
            """),
            {"month_key": month_key}
        ).fetchall()
        
        if not current_categories:
            logger.info(f"No category metrics found for {month_key}, skipping anomaly scan")
            return 0
        
        anomaly_count = 0
        threshold = 50.0  # 50% порог по умолчанию (D-17)
        min_baseline_amount = 10.0  # Минимальный baseline для фильтрации шума (D-17)
        
        for category_row in current_categories:
            category = category_row[0]
            current_val = float(category_row[1])
            
            # Получаем baseline за 3 предыдущих месяца
            baseline_result = db.execute(
                text(f"""
                    SELECT AVG(total) as avg_total, COUNT(*) as month_count
                    FROM category_metrics 
                    WHERE month_key IN ({prev_months_str}) 
                    AND category = :category
                """),
                {"category": category}
            ).fetchone()
            
            if not baseline_result:
                continue
                
            baseline_avg = baseline_result[0]
            month_count = baseline_result[1]
            
            # Guard 1: Проверяем достаточность истории
            if month_count < 3:
                logger.debug(f"Insufficient history for category {category}: {month_count}/3 months")
                continue
            
            # Guard 2: Проверяем валидность baseline
            if baseline_avg is None or baseline_avg <= 0:
                logger.debug(f"Invalid baseline for category {category}: {baseline_avg}")
                continue
            
            # Guard 3: Фильтр шума на мелких категориях (D-17)
            if baseline_avg < min_baseline_amount:
                logger.debug(f"Baseline too small for category {category}: ${baseline_avg:.2f} < ${min_baseline_amount}")
                continue
            
            # Guard 4: Только расходные транзакции (отрицательные или положительные?)
            # В category_metrics.total хранятся абсолютные значения расходов (положительные)
            # Проверяем что current_val > 0 (расходы есть)
            if current_val <= 0:
                continue
            
            # Вычисляем процент отклонения
            delta_pct = ((current_val - baseline_avg) / baseline_avg) * 100
            
            # Проверяем порог
            if delta_pct > threshold:
                # Дедупликация: проверяем, не существует ли уже аномалия для этой категории в этом месяце
                existing = db.execute(
                    text("""
                        SELECT id FROM anomaly_events 
                        WHERE month_key = :month_key AND category = :category
                    """),
                    {"month_key": month_key, "category": category}
                ).fetchone()
                
                detected_at = datetime.utcnow().isoformat()
                
                if existing:
                    # Обновляем существующую запись
                    db.execute(
                        text("""
                            UPDATE anomaly_events 
                            SET current_val = :current_val, 
                                baseline_val = :baseline_val, 
                                delta_pct = :delta_pct,
                                threshold = :threshold,
                                detected_at = :detected_at,
                                status = 'new'
                            WHERE month_key = :month_key AND category = :category
                        """),
                        {
                            "month_key": month_key,
                            "category": category,
                            "current_val": current_val,
                            "baseline_val": baseline_avg,
                            "delta_pct": delta_pct,
                            "threshold": threshold,
                            "detected_at": detected_at
                        }
                    )
                else:
                    # Создаём новую запись
                    db.execute(
                        text("""
                            INSERT INTO anomaly_events 
                            (month_key, category, current_val, baseline_val, delta_pct, threshold, status, detected_at)
                            VALUES (:month_key, :category, :current_val, :baseline_val, :delta_pct, :threshold, :status, :detected_at)
                        """),
                        {
                            "month_key": month_key,
                            "category": category,
                            "current_val": current_val,
                            "baseline_val": baseline_avg,
                            "delta_pct": delta_pct,
                            "threshold": threshold,
                            "status": "new",
                            "detected_at": detected_at
                        }
                    )
                
                anomaly_count += 1
                logger.info(
                    f"Anomaly detected for {month_key}/{category}: "
                    f"${current_val:.2f} vs baseline ${baseline_avg:.2f} "
                    f"(+{delta_pct:.1f}% > {threshold}%)"
                )
        
        db.commit()
        
        if anomaly_count > 0:
            logger.info(f"Anomaly scan for {month_key}: detected {anomaly_count} anomalies")
        else:
            logger.info(f"Anomaly scan for {month_key}: no anomalies detected")
        
        return anomaly_count
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error scanning anomalies for {month_key}: {e}")
        raise
    finally:
        db.close()