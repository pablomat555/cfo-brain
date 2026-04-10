# TASK: Fix SQLAlchemy text() wrapper in metrics_service.py

**Создан:** 09 апреля 2026, 21:05 (Kyiv)
**Уровень:** L1
**Статус:** pending

## Цель
Исправить `analytics/metrics_service.py` — обернуть все строковые SQL запросы в `text()` для совместимости с SQLAlchemy 2.x. После исправления backfill скрипт должен работать без ошибок.

## Scope
Файлы и директории в scope:
- `analytics/metrics_service.py` (добавить `from sqlalchemy import text` и обернуть два вызова `db.execute("` в `text()`)
- `analytics/anomaly_service.py` (проверить, что все вызовы уже используют `text()`)

Вне scope (не трогать):
- Все остальные файлы
- Изменение логики SQL запросов
- Исправление f-string инъекции в anomaly_service.py (строка 72)

## Шаги
1. Добавить `from sqlalchemy import text` в импорты `analytics/metrics_service.py`
2. Найти два вызова `db.execute("` в строках ~115 и ~137
3. Обернуть SQL строки в `text()`: `db.execute(text("""..."""), params)`
4. Проверить, что в `analytics/anomaly_service.py` все вызовы уже используют `text()` (уже есть)
5. Запушить изменения
6. Дождаться деплоя на VPS
7. Повторить выполнение backfill скрипта: `docker exec cfo-brain-cfo_api-1 python3 -m scripts.backfill_metrics`
8. Убедиться, что вывод "Backfill complete. Processed 5 months." без ошибок
9. Повторный запуск скрипта → вывод "Nothing to backfill"
10. Проверить `/trends` в боте

## Definition of Done
- [ ] `analytics/metrics_service.py` исправлен, добавлен импорт `text`
- [ ] Оба вызова `db.execute` обёрнуты в `text()`
- [ ] Backfill скрипт выполняется без ошибок `sqlalchemy.exc.ArgumentError`
- [ ] Вывод показывает успешную обработку 5 месяцев
- [ ] Повторный запуск скрипта: вывод "Nothing to backfill"
- [ ] `/trends` в боте показывает данные за несколько месяцев

## Observations outside scope
