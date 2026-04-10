"""
Одноразовый backfill: пересчитать метрики для месяцев которые есть в
transactions но отсутствуют в monthly_metrics.
Идемпотентен: повторный запуск не создаёт дублей.
Запуск: docker compose run --rm cfo_api python3 scripts/backfill_metrics.py
"""
import sys
from sqlalchemy import text
from core.database import SessionLocal
from analytics.metrics_service import recalculate
from analytics.anomaly_service import scan

def backfill():
    db = SessionLocal()
    try:
        # Только месяцы которых нет в monthly_metrics
        rows = db.execute(text("""
            SELECT DISTINCT strftime('%Y-%m', date) AS month_key
            FROM transactions
            WHERE strftime('%Y-%m', date) NOT IN (
                SELECT month_key FROM monthly_metrics
            )
            ORDER BY month_key
        """))
        months = [row[0] for row in rows.fetchall()]
    finally:
        db.close()

    if not months:
        print("Nothing to backfill — all months already in monthly_metrics.")
        return

    print(f"Found {len(months)} missing months: {months}")

    for month_key in months:
        print(f"Processing {month_key}...")
        try:
            recalculate(month_key)
            scan(month_key)
            print(f"  ✅ {month_key} done")
        except Exception as e:
            print(f"  ❌ {month_key} error: {e}")
            # Продолжаем с остальными месяцами
            continue

    print(f"Backfill complete. Processed {len(months)} months.")

if __name__ == "__main__":
    backfill()