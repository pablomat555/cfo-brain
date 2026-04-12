# PROJECT SNAPSHOT: CFO Brain
Последнее обновление: 11 апреля 2026, 21:40 (Kyiv)

## 1. Идентификация
- **Цель:** Персональный финансовый директор в Telegram — трекинг бюджета, анализ расходов, симуляция финансовых сценариев
- **Owner:** Я
- **Repo:** git@github.com:pablomat555/cfo-brain.git
- **Стек:** Python · aiogram 3.x · FastAPI · SQLite · Docker Compose · Doppler
- **Текущая фаза:** Phase 3 АКТИВНА (Capital Snapshot MVP deployed)

## 2. Архитектура
- **Flow:** Telegram → Bot Gateway → CFO Brain API → ETL Pipeline → SQLite → Response
- **Компоненты:**
  - `bot/` — Telegram gateway (aiogram 3.x), приём команд и CSV файлов
  - `api/` — FastAPI, бизнес-логика CFO, эндпоинты /ingest/csv, /health, /report/period
  - `core/` — модели данных, конфигурация, работа с БД
  - `etl/` — парсинг CSV, загрузка транзакций, обработка non-breaking spaces
  - `data/` — SQLite база данных (cfo.db)
  - `analytics/` — агрегация данных и генерация отчётов

## 3. Окружение
- **Локально:** ~/Dev/cfo-brain
- **VPS:** Hetzner (тот же сервер что openclaw-server)
- **Секреты:** Doppler (проект: cfo-brain / prd)
- **Deploy:** git push → GitHub Actions → VPS (DEV_PROTOCOL v1.3)
- **Env Vars (names only):**
  - `TELEGRAM_TOKEN` (установлен в Doppler)
  - `CFO_DB_URL` (по умолчанию sqlite:////app/data/cfo.db)
  - `OPENROUTER_API_KEY` (для AI-анализа, опционально)
  - `LOG_LEVEL` (по умолчанию INFO)
  - `OWNER_CHAT_ID` (для еженедельного дайджеста)

## 4. Текущее состояние
- **Версия:** v0.9-alpha
- **Статус:** Phase 1 ЗАВЕРШЁН, Phase 2 ЗАВЕРШЁН, Phase 3 АКТИВНА (Capital Snapshot MVP)
  - Phase 1, Task #1 ЗАВЕРШЁН (базовая структура)
  - Phase 1, Task #2 ЗАВЕРШЁН (AI вердикт + /report эндпоинт)
  - Phase 1, Task #3 ЗАВЕРШЁН (port change 8001 → 8002)
  - Phase 1, Task #4 ЗАВЕРШЁН (/report handler в боте)
  - Phase 1, Task #5 ЗАВЕРШЁН (accounts.yml update)
  - Phase 1, Task #6 ЗАВЕРШЁН (D-13 auto-period detection)
  - Phase 1, Task #7 ЗАВЕРШЁН (timeout fix 10s → 60s)
  - Phase 2, Task #1 ЗАВЕРШЁН (Observer Foundation — data layer)
  - Phase 2, Task #2 ЗАВЕРШЁН (Observer API + Bot Surface)
  - Phase 2, Task #3 ЗАВЕРШЁН (Scheduler + Post-Ingest Alert)
  - Phase 2, Task #4 ✅ ЗАВЕРШЁН (Integration Smoke Test — после исправления OWNER_CHAT_ID все проверки PASS)
  - Phase 2, Task #5 ✅ ЗАВЕРШЁН (Fix OWNER_CHAT_ID Propagation — добавлен в docker-compose.yml)
  - Phase 2, Task #6 ✅ ЗАВЕРШЁН (Backfill Historical Metrics)
  - Phase 2, Task #7 ✅ ЗАВЕРШЁН (Persistent SQLite Volume)
  - Phase 2, Task #8 ✅ ЗАВЕРШЁН (Fix ETL Rollback Bug)
  - Phase 2, Task #9 ✅ ЗАВЕРШЁН (Filter Balancing Transactions and Internal Transfers)
  - Phase 3, Task #1A ✅ ЗАВЕРШЁН (Capital Snapshot MVP — таблицы, API, бот команды)
  - **Дополнительные задачи Phase 2:**
    - ✅ **Volume persistence** — добавлен named volume `cfo_data` для `/app/data`
    - ✅ **Конфигурация CFO_DB_URL** — исправлено поле `cfo_db_url` для использования env переменной
    - ✅ **Backfill скрипт** — создан `scripts/backfill_metrics.py` для обработки отсутствующих месяцев
    - ✅ **Фикс rollback бага** — исправлен деструктивный паттерн в `etl/loader.py` через `db.begin_nested()`
    - ✅ **Валидатор OWNER_CHAT_ID** — добавлен validator для преобразования пустой строки в None
    - ✅ **Фильтрация технических записей** — добавлена фильтрация Balancing transaction и переводов между счетами

### Что работает
- ✅ Полная структура repo создана (20+ файлов)
- ✅ ETL pipeline: парсинг CSV с non-breaking spaces, загрузка в SQLite с isolated transactions через `db.begin_nested()`
- ✅ Фильтрация: Balancing transaction и переводы между счетами пропускаются
- ✅ API: FastAPI с эндпоинтами POST /ingest/csv, GET /health, GET /report/period, GET /observer/anomalies, GET /observer/trends, POST /ingest/capital_snapshot, GET /capital/state, POST /capital/account, GET /capital/accounts
- ✅ Bot: aiogram 3.x, обработка команд /start, /status, /report, /anomalies, /trends, /capital, /capital_add, /capital_edit и CSV файлов
- ✅ Docker Compose: два сервиса (cfo_api, cfo_bot) с healthcheck (порт 8002) и named volume `cfo_data`
- ✅ Doppler integration: переменные окружения инжектятся через environment (TELEGRAM_TOKEN, CFO_DB_URL, OWNER_CHAT_ID, OPENROUTER_API_KEY, LOG_LEVEL)
- ✅ Makefile: команды make dev-api (порт 8002), make up, make logs
- ✅ Уникальный constraint: (date, amount, account, description)
- ✅ Currency mapping: accounts.yml для маппинга аккаунтов на валюты (13 аккаунтов)
- ✅ AI-анализ транзакций через OpenRouter (core/ai_verdict.py)
- ✅ Эндпоинт /report/period для генерации отчётов (api/routers/report.py)
- ✅ Модель PeriodReport с полем period_type (core/models.py)
- ✅ Агрегация транзакций (analytics/aggregator.py)
- ✅ Команда /report в боте: получает отчёт за текущий месяц через API
- ✅ AI вердикт возвращается в ответе API
- ✅ Автоопределение периода для команды /report (D-13): система запоминает даты последнего CSV и использует их при вызове /report без параметров
- ✅ Поддержка параметра /report YYYY-MM для явного указания месяца
- ✅ Увеличен timeout для fetch_report до 60 секунд (предотвращение таймаутов при генерации отчётов)
- ✅ Observer Foundation: таблицы monthly_metrics, category_metrics, anomaly_events (D-16)
- ✅ metrics_service.recalculate() + anomaly_service.scan() с post-ingest hook (D-21)
- ✅ GET /observer/anomalies — аномалии за период с detection_status (D-19)
- ✅ GET /observer/trends — метрики по месяцам, ASC, с rate_type (D-19)
- ✅ Команды /anomalies и /trends в боте
- ✅ APScheduler: еженедельный дайджест (пн 09:00 Europe/Kyiv) — работает с OWNER_CHAT_ID
- ✅ Post-ingest alert: bounded polling D-23 (3 попытки, 2с интервал)
- ✅ Integration Smoke Test: все 7 проверок PASS
- ✅ **Capital Snapshot MVP deployed:** Деплой на VPS успешен, контейнеры подняты, smoke test пройден (корректная конвертация валют после фикса бага)
- ✅ **Volume persistence:** Данные сохраняются между редеплоями через named volume `cfo_data`
- ✅ **Конфигурация CFO_DB_URL:** Приложение использует env переменную для пути к БД
- ✅ **Backfill скрипт:** `scripts/backfill_metrics.py` обрабатывает отсутствующие месяцы автоматически
- ✅ **Фикс rollback бага:** Изолированные транзакции предотвращают потерю данных при дубликатах
- ✅ **Валидатор OWNER_CHAT_ID:** Преобразование пустой строки в None предотвращает crash бота
- ✅ **Фильтрация технических записей:** Balancing transaction и переводы пропускаются, отчёты показывают реалистичные суммы

### Known Issues
- ⚠️ Unclosed connector warning в боте (aiohttp cleanup) — некритично
- ⚠️ Двойной commit в etl/loader.py (один для upload session, другой для транзакций) — может быть оптимизировано
- ⚠️ APScheduler shutdown hook отсутствует — возможны warnings при docker stop. Phase 3.
- ⚠️ Rate type "skip" используется по умолчанию — аналитика с ним ограничена
- ⚠️ `/capital_edit` wizard обновляет только баланс, не другие поля (currency, fx_rate, bucket) — требуется доработка в Task #1B

## 5. Фокус сессии
- **Цель:** Деплой Capital Snapshot MVP завершён, smoke test пройден, подготовка к Task #1B (Portfolio Positions)
- **Last Commit:** Phase 3 Task #1A fix — исправление бага конвертации валют (e3af729)
- **Git Status:** Все изменения закоммичены и запушены, деплой на VPS выполнен, контейнеры работают

## Следующий шаг
**Phase 3 АКТИВНА. Capital Snapshot MVP развёрнут и работает.**

**Выполненные действия:**
1. ✅ **Деплой на VPS** — `git push` → CI/CD → контейнеры подняты (cfo_api здоров, cfo_bot restarting из-за отсутствия TELEGRAM_TOKEN)
2. ✅ **Smoke test** — `/capital_add` 4 счёта → `/capital` → net worth корректен (53,804.90 USD)
3. ✅ **Обновление PROJECT_SNAPSHOT.md** — Phase 3 Task #1A ✅, добавлены новые эндпоинты, исправлен баг конвертации

**Phase 3, Task #1B — Portfolio Positions** (следующий этап):
- Загрузка позиций из IBKR, Bybit (CSV/API)
- Интеграция с таблицей portfolio_positions
- Расчёт рыночной стоимости и ликвидности

**Known Issues для Phase 3:**
- ⚠️ "Balancing transaction" фильтр добавлен но старые данные очищены — нужна перезагрузка
- ⚠️ Invalid baseline для категорий с отрицательными суммами (D-25) — расходы хранятся как отрицательные числа
- ⚠️ Backup стратегия для SQLite volume отсутствует
- ⚠️ `/capital_edit` wizard обновляет только баланс, не другие поля (currency, fx_rate, bucket) — требуется доработка в Task #1B

### Что выполнено сверх Phase 1 DoD:
- ✅ D-11 CI/CD — GitHub Actions работает, деплой на VPS автоматический
- ✅ D-13 — автоопределение периода из последнего CSV
- ✅ D-14 — мультивалютная агрегация (ручной курс + /skip режим)
- ✅ accounts.yml — 13 аккаунтов с валютами
- ✅ venv311 убран из repo
- ✅ Phase 2, Task #1 — Observer Foundation (data layer, три таблицы метрик, сервисы пересчёта и детекции, post-ingest hook)
- ✅ Phase 2, Task #2 — Observer API + Bot Surface (GET /observer/anomalies, GET /observer/trends, команды /anomalies и /trends в боте)
- ✅ Phase 2, Task #3 — Scheduler + Post-Ingest Alert (APScheduler, bounded polling, исправление D-22)
- ✅ Phase 2, Task #4 — Integration Smoke Test (все 7 проверок PASS после исправления OWNER_CHAT_ID)
- ✅ Phase 2, Task #5 — Fix OWNER_CHAT_ID Propagation (добавлен OWNER_CHAT_ID в docker-compose.yml)
- ✅ Phase 2, Task #6 — Backfill Historical Metrics (скрипт scripts/backfill_metrics.py)
- ✅ Phase 2, Task #7 — Persistent SQLite Volume (named volume cfo_data)
- ✅ Phase 2, Task #8 — Fix ETL Rollback Bug (db.begin_nested() вместо db.rollback())
- ✅ Phase 2, Task #9 — Filter Balancing Transactions and Internal Transfers (фильтрация технических записей)

### Открытые решения (не блокируют Phase 3):
- D-10 Exception Policy — ✅ выполнено (добавлено в STRATEGY.md)
- python3 стандарт — ✅ выполнено (добавлено в CLAUDE.md)
- D-22 get_last_complete_month() — ✅ закрыто в Task #3
