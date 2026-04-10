# DEV LOG: CFO Brain
Последнее обновление: 10 апреля 2026, 21:57 (Kyiv)

## Phase Transition: Phase 2 → Phase 3
**Дата:** 10 апреля 2026
**Статус:** ✅ ЗАВЕРШЕНО

### Контекст
- **Phase 2 (CI/CD & PRODUCTION)** завершена: все 9 задач выполнены
- **Phase 3 (СТРАТЕГ)** начинается: фокус на стратегическом анализе, рекомендациях и симуляциях
- **Итоги Phase 2:** Полностью production-ready система с CI/CD, Observer pipeline, persistence, исправленными багами и фильтрацией технических записей

### Выполненные работы в Phase 2
1. **Task #1** — Observer Foundation (data layer, три таблицы метрик, сервисы пересчёта и детекции, post-ingest hook)
2. **Task #2** — Observer API + Bot Surface (GET /observer/anomalies, GET /observer/trends, команды /anomalies и /trends в боте)
3. **Task #3** — Scheduler + Post-Ingest Alert (APScheduler, bounded polling, исправление D-22)
4. **Task #4** — Integration Smoke Test (все 7 проверок PASS после исправления OWNER_CHAT_ID)
5. **Task #5** — Fix OWNER_CHAT_ID Propagation (добавлен OWNER_CHAT_ID в docker-compose.yml)
6. **Task #6** — Backfill Historical Metrics (скрипт scripts/backfill_metrics.py)
7. **Task #7** — Persistent SQLite Volume (named volume cfo_data)
8. **Task #8** — Fix ETL Rollback Bug (db.begin_nested() вместо db.rollback())
9. **Task #9** — Filter Balancing Transactions and Internal Transfers (фильтрация технических записей)

### Результаты Phase 2
- ✅ Полная CI/CD pipeline: GitHub Actions → VPS автоматический деплой
- ✅ Observer system: метрики, аномалии, тренды, еженедельный дайджест
- ✅ Production readiness: volume persistence, конфигурация через env переменные
- ✅ Исправление критических багов: rollback в ETL, OWNER_CHAT_ID validator
- ✅ Фильтрация технических записей: Balancing transaction и переводы между счетами пропускаются
- ✅ STRATEGY.md v1.1: добавлена инвестиционная стратегия и финансовые протоколы
- ✅ База данных очищена для чистого старта Phase 3

### Следующий шаг:
- **Phase 3 (СТРАТЕГ):** Стратегический анализ, рекомендации по распределению капитала, симуляции финансовых сценариев
- **Требования:** Загрузка полного CSV с транзакциями (2024-07 — 2026-04) с применением новых фильтров

---

## Сессия: Phase 2, Task #9 — Filter Balancing Transactions and Internal Transfers
**Дата:** 10 апреля 2026
**Участники:** Orchestrator, Engineer
**Статус:** ✅ ЗАВЕРШЕНО

### Контекст
- **Цель:** Добавить фильтрацию технических записей (Balancing transaction) и внутренних переводов в ETL pipeline
- **Проблема:** Общий отчёт показывает нереалистичные суммы ($111,480 за весь период вместо реальных ~$3,800/мес)
- **Причина:** Balancing transaction записи и переводы между счетами считаются как доход/расход
- **Задача:** L2 (средняя) — изменения в нескольких файлах с зависимостями
- **Фаза:** Phase 2 — CI/CD & PRODUCTION (последняя задача перед переходом в Phase 3)

### Выполненные работы
1. **Анализ текущего кода:**
   - Проверен [`etl/parser.py`](etl/parser.py) — фильтрация переводов уже реализована (строки 132-138)
   - Проверен [`etl/loader.py`](etl/loader.py) — класс LoadResult требует добавления поля `skipped_technical`
   - Проверен [`bot/handlers/csv_upload.py`](bot/handlers/csv_upload.py) — ответ бота нужно обновить

2. **Добавлена фильтрация Balancing transaction** в [`etl/parser.py:142-146`](etl/parser.py:142-146):
   ```python
   # Пропускаем технические записи Balancing transaction
   if category == "Balancing transaction":
       logger.info(f"Row {i}: Balancing transaction, skipping")
       continue
   ```

3. **Добавлено поле `skipped_technical`** в класс `LoadResult` в [`etl/loader.py:17`](etl/loader.py:17):
   ```python
   class LoadResult(BaseModel):
       """Результат загрузки транзакций"""
       inserted: int = 0
       skipped_duplicates: int = 0
       skipped_technical: int = 0  # НОВОЕ ПОЛЕ
       errors: int = 0
       detection_status: str = "pending"
   ```

4. **Обновлён ответ бота** в [`bot/handlers/csv_upload.py:90-97`](bot/handlers/csv_upload.py:90-97):
   ```python
   reply_text = (
       f"✅ Загружено: {inserted} транзакций.\n"
       f"📋 Дублей пропущено: {skipped}.\n"
       f"⚙️ Технических записей пропущено: {skipped_technical}.\n"
       f"⚠️ Ошибок: {errors}."
   )
   ```

5. **Тестирование:**
   - Создан тестовый скрипт `test_filtering_simple.py` для проверки логики фильтрации
   - Проверена компиляция: `python3 -m py_compile etl/loader.py` и `python3 -m py_compile etl/parser.py` успешно
   - Фильтрация работает: пропускает 1 Balancing transaction и 2 перевода, оставляет 2 обычные транзакции

### Технические детали
- **Локализация изменений:**
  - `etl/parser.py` — добавлена фильтрация Balancing transaction
  - `etl/loader.py` — добавлено поле `skipped_technical` в LoadResult
  - `bot/handlers/csv_upload.py` — обновлён ответ бота
- **Обратная совместимость:** Поле `skipped_technical` имеет значение по умолчанию 0, API response автоматически включает его через `response_model=LoadResult`
- **Фильтрация переводов:** Уже была реализована в парсере (строки 132-138), осталась без изменений

### Результаты
- **Definition of Done выполнены:** Все чекбоксы TASK.md отмечены
- **PROJECT_SNAPSHOT.md обновлён:** Версия v0.9-alpha, Phase 2 завершён, Phase 3 активна
- **STRATEGY.md добавлен:** Инвестиционная стратегия v1.1 закоммичена в репозиторий
- **Git операции:**
  - Commit: "docs: add investment portfolio strategy v1.1" (20ac056)
  - Push: успешно выполнен на ветку main
- **База данных очищена:** Выполнена SSH команда на сервер для очистки всех таблиц

### Валидация
1. **Фильтрация Balancing transaction:** Записи с Category="Balancing transaction" пропускаются при парсинге CSV
2. **Фильтрация переводов:** Записи с непустым Transfer Account продолжают пропускаться (существующая логика)
3. **LoadResult:** Содержит поле `skipped_technical: int`
4. **Ответ бота:** Показывает "⚙️ Технических записей пропущено: X"
5. **Компиляция:** `python3 -m py_compile` проходит для всех изменённых файлов

---

## Сессия: Phase 2, Task #8 — Fix ETL Rollback Bug
**Дата:** 10 апреля 2026
**Участники:** Orchestrator, Engineer
**Статус:** ✅ ЗАВЕРШЕНО

### Контекст
- **Цель:** Исправить деструктивный rollback паттерн в ETL pipeline, который уничтожал ранее вставленные записи
- **Проблема:** Бот сообщал "✅ Загружено: 1680 транзакций", но в БД оставалось только 433 записи
- **Root cause:** `db.rollback()` внутри цикла обработки строк откатывал всю внешнюю транзакцию
- **Задача:** L2 (средняя) — требуется понимание SQLAlchemy nested transactions
- **Фаза:** Phase 2 — CI/CD & PRODUCTION

### Выполненные работы
1. **Прочитан [`etl/loader.py`](etl/loader.py)** и найден деструктивный паттерн
2. **Исправлен цикл загрузки транзакций** через `db.begin_nested()`:
   ```python
   for row in rows:
       with db.begin_nested():  # ← изолированная транзакция для каждой строки
           try:
               # ... создание transaction ...
               db.add(transaction)
               db.flush()
               result.inserted += 1
           except IntegrityError:
               # nested transaction автоматически откатывается
               result.skipped_duplicates += 1
   ```
3. **Убраны лишние commit-паттерны** для чистоты кода
4. **Протестирована загрузка CSV:** Теперь все 1680+ транзакций сохраняются корректно

### Результаты
- **Definition of Done выполнены:** Все чекбоксы TASK.md отмечены
- **PROJECT_SNAPSHOT.md обновлён:** Добавлена Task #8, версия v0.8-alpha
- **Git commit:** Зафиксировано исправление rollback бага

---

## Сессия: Phase 2, Task #7 — Persistent SQLite Volume
**Дата:** 10 апреля 2026
**Участники:** Orchestrator, Engineer
**Статус:** ✅ ЗАВЕРШЕНО

### Контекст
- **Цель:** Обеспечить сохранение данных SQLite между редеплоями через named Docker volume
- **Проблема:** При каждом `docker compose up --build` данные терялись
- **Решение:** Добавить named volume `cfo_data` и монтировать его на `/app/data`
- **Задача:** L1 (простая) — изменения только в docker-compose.yml
- **Фаза:** Phase 2 — CI/CD & PRODUCTION

### Выполненные работы
1. **Обновлён [`docker-compose.yml`](docker-compose.yml):**
   ```yaml
   volumes:
     cfo_data:
   
   services:
     cfo_api:
       volumes:
         - cfo_data:/app/data
   ```
2. **Проверена persistence:** После перезапуска контейнеров данные сохраняются
3. **Обновлена конфигурация CFO_DB_URL:** Использование env переменной для пути к БД

### Результаты
- **Definition of Done выполнены:** Все чекбоксы TASK.md отмечены
- **PROJECT_SNAPSHOT.md обновлён:** Добавлена Task #7
- **Git commit:** Зафиксированы изменения volume persistence

---

## Сессия: Phase 2, Task #6 — Backfill Historical Metrics
**Дата:** 10 апреля 2026
**Участники:** Orchestrator, Engineer
**Статус:** ✅ ЗАВЕРШЕНО

### Контекст
- **Цель:** Создать скрипт для пересчёта метрик за отсутствующие месяцы
- **Проблема:** После очистки БД или добавления новых категорий метрики не пересчитываются автоматически
- **Решение:** Скрипт `scripts/backfill_metrics.py`, который проходит по всем месяцам и вызывает `recalculate()`
- **Задача:** L1 (простая) — один файл, простой алгоритм
- **Фаза:** Phase 2 — CI/CD & PRODUCTION

### Выполненные работы
1. **Создан [`scripts/backfill_metrics.py`](scripts/backfill_metrics.py):**
   ```python
   def backfill(start_date="2024-07", end_date=None):
       # Определяет все месяцы между start_date и end_date
       # Для каждого месяца вызывает metrics_service.recalculate(month_key)
   ```
2. **Интегрирован в Makefile:** Команда `make backfill`
3. **Протестирован:** Корректно обрабатывает отсутствующие месяцы, выводит "Nothing to backfill" при полной синхронизации

### Результаты
- **Definition of Done выполнены:** Все чекбоксы TASK.md отмечены
- **PROJECT_SNAPSHOT.md обновлён:** Добавлена Task #6
- **Git commit:** Зафиксирован backfill скрипт

---

## Сессия: Phase 2, Task #5 — Fix OWNER_CHAT_ID Propagation
**Дата:** 10 апреля 2026
**Участники:** Orchestrator, Engineer
**Статус:** ✅ ЗАВЕРШЕНО

### Контекст
- **Цель:** Исправить propagation переменной OWNER_CHAT_ID из Doppler в docker-compose.yml
- **Проблема:** Переменная не передавалась в контейнер бота, scheduler не мог отправлять еженедельный дайджест
- **Решение:** Добавить `OWNER_CHAT_ID: ${OWNER_CHAT_ID}` в environment бота в docker-compose.yml
- **Задача:** L1 (простая) — одно изменение в docker-compose.yml
- **Фаза:** Phase 2 — CI/CD & PRODUCTION

### Выполненные работы
1. **Обновлён [`docker-compose.yml`](docker-compose.yml):**
   ```yaml
   cfo_bot:
     environment:
       OWNER_CHAT_ID: ${OWNER_CHAT_ID}
   ```
2. **Проверена работа scheduler:** Еженедельный дайджест отправляется корректно
3. **Добавлен validator** для обработки пустой строки в [`core/config.py`](core/config.py)

### Результаты
- **Definition of Done выполнены:** Все чекбоксы TASK.md отмечены
- **PROJECT_SNAPSHOT.md обновлён:** Добавлена Task #5
- **Git commit:** Зафиксировано исправление OWNER_CHAT_ID propagation

---

## Сессия: Phase 2, Task #4 — Integration Smoke Test
**Дата:** 10 апреля 2026
**Участники:** Orchestrator, Engineer
**Статус:** ✅ ЗАВЕРШЕНО

### Контекст
- **Цель:** Провести интеграционный smoke test всех компонентов системы
- **Проблема:** После множества изменений требовалась проверка end-to-end работоспособности
- **Решение:** 7 проверок от healthcheck до аномалий
- **Задача:** L2 (средняя) — требует понимания всей системы
- **Фаза:** Phase 2 — CI/CD & PRODUCTION

### Выполненные работы
1. **Разработаны 7 проверок:**
   1. Healthcheck (`GET /health`)
   2. CSV ingest (`POST /ingest/csv`)
   3. Period report (`GET /report/period`)
   4. Observer anomalies (`GET /observer/anomalies`)
   5. Observer trends (`GET /observer/trends`)
   6. Scheduler (проверка конфигурации)
   7. Volume persistence (проверка сохранения данных)
2. **Все проверки PASS** после исправления OWNER_CHAT_ID
3. **Документированы результаты** в PROJECT_SNAPSHOT.md

### Результаты
- **Definition of Done выполнены:** Все чекбоксы TASK.md отмечены
- **PROJECT_SNAPSHOT.md обновлён:** Добавлена Task #4
- **Git commit:** Зафиксированы результаты smoke test

---

## Сессия: Phase 2, Task #3 — Scheduler + Post-Ingest Alert
**Дата:** 10 апреля 2026
**Участники:** Orchestrator, Engineer
**Статус:** ✅ ЗАВЕРШЕНО

### Контекст
- **Цель:** Реализовать APScheduler для еженедельного дайджеста и bounded polling для post-ingest alert
- **Проблема:** D-22 (get_last_complete_month) возвращал некорректный месяц
- **Решение:** Исправить логику определения последнего полного месяца
- **Задача:** L2 (средняя) — несколько компонентов, временная логика
- **Фаза:** Phase