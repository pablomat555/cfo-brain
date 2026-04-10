# TASK: Phase 2, Task #9 — Filter Balancing Transactions and Internal Transfers

**Создан:** 10 апреля 2026, 21:23 (Kyiv)
**Уровень:** L2
**Статус:** pending

## Цель
Добавить фильтрацию технических записей (Balancing transaction) и внутренних переводов в ETL pipeline, чтобы общий отчёт показывал реалистичные суммы доходов/расходов.

## Scope
Файлы и директории в scope:
- `etl/parser.py` — добавить фильтрацию Balancing transaction
- `etl/loader.py` — добавить поле `skipped_technical` в LoadResult
- `api/routers/ingest.py` — response_model автоматически подхватит новое поле
- `bot/handlers/csv_upload.py` — обновить ответ бота для показа skipped_technical

Вне scope (не трогать):
- Все остальные файлы
- Изменения в analytics, metrics_service, anomaly_service
- Изменения в docker-compose, Doppler, volume
- Рефакторинг ETL pipeline
- Фильтрация других категорий

## Проблема
Общий отчёт показывает нереалистичные суммы:
- Доходы $111,480 за весь период вместо реальных ~$3,800/мес
- Причина: Balancing transaction записи и переводы между счетами считаются как доход/расход хотя это технические операции

Примеры из CSV:
- "24 July 2024","","Balancing transaction","","","","Binance","","40 000,00"
- "20 March 2026","","","","","","Bybit*","Моно 8235","-1 000,00" ← Transfer Account заполнен
- "20 March 2026","","","","","","Моно 8235","Bybit*","44 500,00" ← Transfer Account заполнен

## Текущее состояние
1. **Фильтрация переводов уже реализована** в `etl/parser.py` (строки 132-138):
   ```python
   transfer_account = row.get("Transfer Account", "").strip()
   is_transfer = bool(transfer_account)
   if is_transfer:
       logger.info(f"Row {i}: transfer transaction..., skipping")
       continue
   ```
2. **Фильтрация Balancing transaction отсутствует** — нужно добавить
3. **LoadResult** в `etl/loader.py` содержит поля: `inserted`, `skipped_duplicates`, `errors`, `detection_status`
4. **Ответ бота** в `bot/handlers/csv_upload.py` показывает только `inserted`, `skipped_duplicates`, `errors`

## Решение

### Правило 1: Пропускать Balancing transaction
Добавить в `etl/parser.py` после парсинга категории:
```python
category = row.get("Category", "").strip() or None

# Пропускаем технические записи Balancing transaction
if category == "Balancing transaction":
    logger.info(f"Row {i}: Balancing transaction, skipping")
    continue
```

### Правило 2: Уже реализовано — пропускать переводы между счетами
(Оставить существующую логику)

### Обновление LoadResult
В `etl/loader.py` добавить поле `skipped_technical` в класс `LoadResult`:
```python
class LoadResult(BaseModel):
    """Результат загрузки транзакций"""
    inserted: int = 0
    skipped_duplicates: int = 0
    skipped_technical: int = 0  # НОВОЕ ПОЛЕ
    errors: int = 0
    detection_status: str = "pending"  # 'pending' | 'running' | 'completed' | 'error' | 'skip_mode'
```

### Обновление ответа бота
В `bot/handlers/csv_upload.py` обновить формирование ответа:
```python
inserted = result.get("inserted", 0)
skipped = result.get("skipped_duplicates", 0)
skipped_technical = result.get("skipped_technical", 0)  # НОВОЕ
errors = result.get("errors", 0)

reply_text = (
    f"✅ Загружено: {inserted} транзакций.\n"
    f"📋 Дублей пропущено: {skipped}.\n"
    f"⚙️ Технических записей пропущено: {skipped_technical}.\n"
    f"⚠️ Ошибок: {errors}."
)
```

## Шаги
1. Прочитать `etl/parser.py` и добавить фильтрацию Balancing transaction после парсинга категории
2. Прочитать `etl/loader.py` и добавить поле `skipped_technical` в класс `LoadResult`
3. Проверить, что `api/routers/ingest.py` использует `response_model=LoadResult` — новое поле автоматически будет включено в JSON ответ
4. Обновить `bot/handlers/csv_upload.py` для показа `skipped_technical` в ответе бота
5. Протестировать изменения локально:
   - `python3 -m py_compile etl/loader.py`
   - `python3 -m py_compile etl/parser.py`
   - Проверить, что код компилируется без ошибок

## Definition of Done
- [ ] Записи с Category="Balancing transaction" пропускаются при парсинге CSV
- [ ] Записи с непустым Transfer Account продолжают пропускаться (существующая логика)
- [ ] `LoadResult` содержит поле `skipped_technical: int`
- [ ] Ответ бота показывает: "⚙️ Технических записей пропущено: X"
- [ ] `python3 -m py_compile etl/loader.py` проходит
- [ ] `python3 -m py_compile etl/parser.py` проходит
- [ ] После деплоя: очистить БД, перезагрузить CSV, проверить что общий отчёт показывает реалистичные суммы

## Observations outside scope
(Engineer заполняет в конце - наблюдения вне scope, не применённые)

---

**Примечание:** Это L2 задача — требуется approve плана перед реализацией.