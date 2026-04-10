# PROJECT SNAPSHOT: CFO Brain
Последнее обновление: 10 апреля 2026, 21:04 (Kyiv)

## 1. Идентификация
- **Цель:** Персональный финансовый директор в Telegram — трекинг бюджета, анализ расходов, симуляция финансовых сценариев
- **Owner:** Я
- **Repo:** git@github.com:pablomat555/cfo-brain.git
- **Стек:** Python · aiogram 3.x · FastAPI · SQLite · Docker Compose · Doppler
- **Текущая фаза:** Phase 2 — CI/CD & PRODUCTION

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
  - `CFO_DB_URL` (по умолчанию sqlite:///./data/cfo.db)
  - `OPENROUTER_API_KEY` (для AI-анализа, опционально)
  - `LOG_LEVEL` (по умолчанию INFO)
  - `OWNER_CHAT_ID` (для еженедельного дайджеста)

## 4. Текущее состояние
- **Версия:** v0.8-alpha
- **Статус:** Phase 1 ЗАВЕРШЁН, Phase 2 ЗАВЕРШЁН, Phase 3 ГОТОВ К СТАРТУ
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
  - **Дополнительные задачи Phase 2:**
    - ✅ **Volume persistence** — добавлен named volume `cfo_data` для `/app/data`
    - ✅ **Конфигурация CFO_DB_URL** — исправлено поле `cfo_db_url` для использования env переменной
    - ✅ **Backfill скрипт** — создан `scripts/backfill_metrics.py` для обработки отсутствующих месяцев
    - ✅ **Фикс rollback бага** — исправлен деструктивный паттерн в `etl/loader.py` через `db.begin_nested()`
    - ✅ **Валидатор OWNER_CHAT_ID** — добавлен validator для преобразования пустой строки в None

### Что работает
- ✅ Полная структура repo создана (20+ файлов)
- ✅ ETL pipeline: парсинг CSV с non-breaking spaces, загрузка в SQLite с isolated transactions через `db.begin_nested()`
- ✅ API: FastAPI с эндпоинтами POST /ingest/csv, GET /health, GET /report/period, GET /observer/anomalies, GET /observer/trends
- ✅ Bot: aiogram 3.x, обработка команд /start, /status, /report, /anomalies, /trends и CSV файлов
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
- ✅ **Volume persistence:** Данные сохраняются между редеплоями через named volume `cfo_data`
- ✅ **Конфигурация CFO_DB_URL:** Приложение использует env переменную для пути к БД
- ✅ **Backfill скрипт:** `scripts/backfill_metrics.py` обрабатывает отсутствующие месяцы автоматически
- ✅ **Фикс rollback бага:** Изолированные транзакции предотвращают потерю данных при дубликатах
- ✅ **Валидатор OWNER_CHAT_ID:** Преобразование пустой строки в None предотвращает crash бота

### Known Issues
- ⚠️ Unclosed connector warning в боте (aiohttp cleanup) — некритично
- ⚠️ Двойной commit в etl/loader.py (один для upload session, другой для транзакций) — может быть оптимизировано
- ⚠️ APScheduler shutdown hook отсутствует — возможны warnings при docker stop. Phase 3.
- ⚠️ Rate type "skip" используется по умолчанию — аналитика с ним ограничена

## 5. Фокус сессии
- **Цель:** Завершить Phase 2, финализировать все технические долги, подготовить систему к Phase 3 (СТРАТЕГ)
- **Last Commit:** Phase 2 complete — ETL rollback fix, volume persistence, DB path fix, OWNER_CHAT_ID validator (7b20e4e)
- **Git Status:** Все изменения закоммичены и запушены, деплой на VPS выполнен, БД очищена для чистого старта

## Следующий шаг
**Phase 2 ЗАВЕРШЁН.** Все задачи Phase 2 выполнены, включая дополнительные фиксы:
1. Volume persistence для сохранения данных между редеплоями
2. Конфигурация CFO_DB_URL для корректного использования env переменных
3. Backfill скрипт для обработки исторических данных
4. Фикс критического rollback бага в ETL pipeline
5. Валидатор OWNER_CHAT_ID для стабильной работы бота

**Phase 3 (СТРАТЕГ)** готов к запуску. Требуется:
1. Загрузка полного CSV с транзакциями (2024-07 — 2026-04)
2. Накопление 2-3 месяцев истории для обучения моделей
3. Настройка курсов валют для корректной аналитики

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

### Открытые решения (не блокируют Phase 3):
- D-10 Exception Policy — ✅ выполнено (добавлено в STRATEGY.md)
- python3 стандарт — ✅ выполнено (добавлено в CLAUDE.md)
- D-22 get_last_complete_month() — ✅ закрыто в Task #3
