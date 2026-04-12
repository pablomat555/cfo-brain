# TASK: Phase 3 / Task #5 — Fix D-25 (Negative Baseline for Expense Categories)

**Создан:** 12 апреля 2026, 20:51 (Kyiv)
**Уровень:** L2
**Статус:** pending

## Цель
Исправить агрегацию расходных категорий в category_metrics.total, чтобы значения были положительными, что позволит anomaly_service корректно вычислять baseline и детектировать аномалии.

## Scope
Файлы и директории в scope:
- `analytics/metrics_service.py` (основное изменение)
- `scripts/backfill_metrics.py` (запуск пересчёта)

Вне scope (не трогать):
- все остальные файлы
- raw transactions (D-15 иммутабельность)
- anomaly_service.py (только использует данные)
- analytics/aggregator.py (для отчётов)

## Шаги
1. **Найти точное место агрегации** - уже найдено: `analytics/metrics_service.py` строки 70-71
2. **Применить ABS() для расходов**:
   ```python
   # БЫЛО:
   category_totals[category] = category_totals.get(category, 0.0) + amount
   
   # СТАЛО:
   category_totals[category] = category_totals.get(category, 0.0) + (abs(amount) if amount < 0 else amount)
   ```
   Правило: amount < 0 → расход → abs(amount); amount > 0 → доход → amount (положительный)
3. **Запустить backfill исторических метрик**:
   ```bash
   docker exec cfo-brain-cfo_api-1 python3 -m scripts.backfill_metrics
   ```
4. **Проверить результат**:
   - Убедиться, что category_metrics.total содержит положительные значения
   - Проверить, что GET /observer/anomalies возвращает detection_status != 'insufficient_history'
   - Убедиться, что аномалии детектируются при наличии превышения порога

## Definition of Done
- [ ] category_metrics.total содержит положительные значения для расходных категорий
- [ ] anomaly_service.scan() не возвращает insufficient_history при наличии 3+ месяцев истории
- [ ] /anomalies возвращает реальные аномалии (или пустой список если нет превышений)
- [ ] backfill выполнен на VPS
- [ ] smoke test: GET /observer/anomalies возвращает detection_status != 'insufficient_history'

## Observations outside scope
1. **Локальный backfill невозможен** — данные находятся на VPS в Docker volume. Для применения фикса необходимо:
   - Сделать git push → CI/CD задеплоит изменения на VPS
   - Выполнить на VPS: `docker exec cfo-brain-cfo_api-1 python3 -m scripts.backfill_metrics`
2. **Проверка результата требует данных** — локальная БД содержит только тестовые транзакции (54 записи), но таблицы monthly_metrics и category_metrics отсутствуют. Для полноценной проверки нужен backfill на продакшн-данных.
3. **Smoke test требует запущенного API** — локальный сервер не запущен, проверка через GET /observer/anomalies невозможна без деплоя.
4. **Категория "Unknown" может содержать смешанные доходы/расходы** — в текущей реализации категория "Unknown" агрегируется без учёта знака, что может искажать метрики если в ней есть как доходы так и расходы.