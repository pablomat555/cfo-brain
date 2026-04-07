# PROJECT SNAPSHOT: CFO Brain
Последнее обновление: 2026-04-07T17:39:45Z

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

## 4. Текущее состояние
- **Версия:** v0.4-alpha
- **Статус:** Phase 1, Task #1 ЗАВЕРШЁН, Task #2 ЗАВЕРШЁН, Task #3 (port change) ЗАВЕРШЁН, Task #4 (/report handler) ЗАВЕРШЁН, Task #5 (accounts.yml update) ЗАВЕРШЁН

### Что работает
- ✅ Полная структура repo создана (14+ файлов)
- ✅ ETL pipeline: парсинг CSV с non-breaking spaces, загрузка в SQLite
- ✅ API: FastAPI с эндпоинтами POST /ingest/csv, GET /health, GET /report/period
- ✅ Bot: aiogram 3.x, обработка команд /start, /status, /report и CSV файлов
- ✅ Docker Compose: два сервиса (cfo_api, cfo_bot) с healthcheck (порт 8002)
- ✅ Doppler integration: переменные окружения инжектятся через environment
- ✅ Makefile: команды make dev-api (порт 8002), make up, make logs
- ✅ Уникальный constraint: (date, amount, account, description)
- ✅ Currency mapping: accounts.yml для маппинга аккаунтов на валюты (13 аккаунтов)
- ✅ AI-анализ транзакций через OpenRouter (core/ai_verdict.py)
- ✅ Эндпоинт /report/period для генерации отчётов (api/routers/report.py)
- ✅ Модель PeriodReport с полем period_type (core/models.py)
- ✅ Агрегация транзакций (analytics/aggregator.py)
- ✅ Команда /report в боте: получает отчёт за текущий месяц через API
- ✅ AI вердикт возвращается в ответе API (исправлено в коммите ab9cfd0)

### Known Issues
- ⚠️ Unclosed connector warning в боте (aiohttp cleanup) — некритично
- ⚠️ Команда /report не поддерживает автоопределение периода из последнего CSV (D-13) — требуется реализация

## 5. Фокус сессии
- **Цель:** Реализация D-13 — улучшение команды /report с автоопределением периода
- **Last Commit:** bea4434 — "Update accounts.yml with 13 accounts mapping" (2026-04-07)
- **Git Status:** Есть нескоммиченные изменения: TASK.md удалён (архивирован в docs/tasks/), docs/tasks/TASK_2026-04-07_ai-verdict-fix.md добавлен

### Definition of Done (Phase 1, Task #5 — accounts.yml update)
- [x] Обновлён accounts.yml с 13 аккаунтами
- [x] Добавлены все соответствующие записи в parser_types
- [x] Добавлен комментарий о процессе добавления новых аккаунтов
- [x] Изменения закоммичены и запушены в репозиторий

## Следующий шаг
**D-13: /report с автоопределением периода из последнего CSV**
- [ ] Создать таблицу upload_sessions в БД
- [ ] Обновить core/models.py — модель UploadSession
- [ ] Обновить core/database.py — создание таблицы
- [ ] Обновить etl/loader.py — сохранять upload session после загрузки
- [ ] Обновить api/routers/report.py — читать последний upload session если период не указан
- [ ] Обновить bot/handlers/commands.py — парсить опциональный параметр /report YYYY-MM
- [ ] Протестировать автоопределение периода
- [ ] Закоммитить и запушить изменения
