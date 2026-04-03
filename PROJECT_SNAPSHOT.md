# PROJECT SNAPSHOT: CFO Brain
Последнее обновление: 2026-04-03T18:52:30Z

## 1. Идентификация
- **Цель:** Персональный финансовый директор в Telegram — трекинг бюджета, анализ расходов, симуляция финансовых сценариев
- **Owner:** Я
- **Repo:** git@github.com:pablomat555/cfo-brain.git
- **Стек:** Python · aiogram 3.x · FastAPI · SQLite · Docker Compose · Doppler
- **Текущая фаза:** Phase 1 — АНАЛИТИК (MVP)

## 2. Архитектура
- **Flow:** Telegram → Bot Gateway → CFO Brain API → ETL Pipeline → SQLite → Response
- **Компоненты:**
  - `bot/` — Telegram gateway (aiogram 3.x), приём команд и CSV файлов
  - `api/` — FastAPI, бизнес-логика CFO, эндпоинты /ingest/csv, /health
  - `core/` — модели данных, конфигурация, работа с БД
  - `etl/` — парсинг CSV, загрузка транзакций, обработка non-breaking spaces
  - `data/` — SQLite база данных (cfo.db)

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

## 4. Текущее состояние
- **Версия:** v0.1-alpha
- **Статус:** Phase 1, Task #1 ЗАВЕРШЁН

### Что работает
- ✅ Полная структура repo создана (14+ файлов)
- ✅ ETL pipeline: парсинг CSV с non-breaking spaces, загрузка в SQLite
- ✅ API: FastAPI с эндпоинтом POST /ingest/csv
- ✅ Bot: aiogram 3.x, обработка команд /start, /status и CSV файлов
- ✅ Docker Compose: два сервиса (cfo_api, cfo_bot) с healthcheck
- ✅ Doppler integration: переменные окружения инжектятся через environment
- ✅ Makefile: команды make dev-api, make up, make logs
- ✅ Уникальный constraint: (date, amount, account, description)
- ✅ Currency mapping: accounts.yml для маппинга аккаунтов на валюты

### Known Issues
- ⚠️ Unclosed connector warning в боте (aiohttp cleanup) — некритично
- ⚠️ Нет AI-анализа транзакций (запланировано в Task #2)
- ⚠️ Нет эндпоинта /report для генерации отчётов (запланировано в Task #2)

## 5. Фокус сессии
- **Цель:** Завершение Phase 1, Task #1 и подготовка к Task #2
- **Last Commit:** 0555f01 — "feat: Phase 1 Task #1 — scaffold + ETL pipeline" (2026-04-03)
- **Git Status:** Репозиторий инициализирован, все файлы закоммичены

### Definition of Done (Phase 1, Task #1)
- [x] Структура repo создана (все 14+ файлов)
- [x] make dev-api работает (API поднимается локально)
- [x] POST /ingest/csv принимает CSV и возвращает статистику
- [x] Бот обрабатывает CSV файлы и отправляет их в API
- [x] make up работает с Docker Compose (оба сервиса healthy)
- [x] Doppler переменные инжектятся корректно (без env_file)
- [x] Git репозиторий инициализирован и закоммичен

**COMMAND:** Готов к Task #2 — AI вердикт + /report эндпоинт.
