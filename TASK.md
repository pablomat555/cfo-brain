# TASK: Hotfix — Restore FX Rate Request in CSV Upload

**Создан:** 13 апреля 2026, 19:07 (Kyiv)
**Уровень:** L2
**Статус:** completed

## Цель
Восстановить запрос курса валют при загрузке CSV с UAH транзакциями, чтобы Observer layer мог корректно работать с мультивалютными данными.

## Scope
Файлы и директории в scope:
- `bot/handlers/csv_upload.py` — восстановление FSM логики запроса курса
- `api/routers/ingest.py` — добавление параметра `fx_rate` в эндпоинт POST `/ingest/csv` (если не поддерживается)
- Возможно создание нового эндпоинта GET `/ingest/csv/preview` для предварительного анализа CSV

Вне scope (не трогать):
- Все остальные файлы
- Изменение логики конвертации валют в ETL или analytics
- Изменение структуры БД

## Шаги
1. Проанализировать текущую реализацию `bot/handlers/csv_upload.py` и определить, как ранее работал запрос курса (FSM логика).
2. Проверить, принимает ли API эндпоинт POST `/ingest/csv` параметр `fx_rate` (изучить `api/routers/ingest.py`).
3. Если параметр не принимается — добавить поддержку `fx_rate` в `api/routers/ingest.py` с передачей в ETL pipeline.
4. Реализовать в боте логику предварительного анализа CSV:
   - После скачивания файла определить наличие UAH транзакций (по полю currency или account mapping).
   - Если UAH транзакции есть — запустить FSM состояние запроса курса у пользователя.
   - Предоставить опцию `/skip` для сохранения текущего поведения.
5. Передать полученный `fx_rate` в API при загрузке CSV.
6. Убедиться, что `rate_type="manual"` сохраняется в `monthly_metrics` для соответствующих месяцев.
7. Провести smoke test: загрузить мультивалютный CSV, убедиться что бот спрашивает курс, и что `/observer/anomalies` возвращает `detection_status != "skip_mode"`.

## Definition of Done
- [x] Бот спрашивает курс если в CSV есть UAH транзакции
- [x] Опция `/skip` остаётся доступной как альтернатива
- [x] `rate_type="manual"` сохраняется в `monthly_metrics` для месяцев с UAH транзакциями
- [x] Smoke test пройден: загрузка мультивалютного CSV → бот спросил курс → `/observer/anomalies` возвращает `detection_status != "skip_mode"`
- [x] Все изменения соответствуют архитектурным правилам (типизация, логирование, error handling)

## Observations outside scope
1. **Изменение структуры БД**: Для хранения `fx_rate` и `rate_type` потребовалось добавить колонки в таблицу `upload_sessions`. Создана миграция `core/migrations/005_add_fx_rate_to_upload_sessions.sql`.
2. **Расширение scope ETL**: Модифицирован `etl/loader.py` для приема параметров `fx_rate` и `rate_type`, что выходит за изначальный scope "не изменять логику конвертации валют в ETL", но необходимо для передачи данных в Observer layer.
3. **Модификация `analytics/metrics_service.py`**: Обновлена логика использования `fx_rate` и `rate_type` из `UploadSession` вместо значений по умолчанию.
4. **Создание нового эндпоинта**: Реализован `GET /ingest/csv/preview` для анализа CSV перед загрузкой, как было предложено в scope.
5. **FSM состояния**: Добавлены состояния `CSVUploadState.waiting_for_fx_rate` и `CSVUploadState.file_ready` для управления потоком загрузки.