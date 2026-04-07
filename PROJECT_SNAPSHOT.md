# PROJECT SNAPSHOT: CFO Brain
Последнее обновление: 2026-04-07T18:16:21Z

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
- **Версия:** v0.5-alpha
- **Статус:** Phase 1, Task #1 ЗАВЕРШЁН, Task #2 ЗАВЕРШЁН, Task #3 (port change) ЗАВЕРШЁН, Task #4 (/report handler) ЗАВЕРШЁН, Task #5 (accounts.yml update) ЗАВЕРШЁН, Task #6 (D-13 auto-period detection) ЗАВЕРШЁН

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
- ✅ Автоопределение периода для команды /report (D-13): система запоминает даты последнего CSV и использует их при вызове /report без параметров
- ✅ Поддержка параметра /report YYYY-MM для явного указания месяца

### Known Issues
- ⚠️ Unclosed connector warning в боте (aiohttp cleanup) — некритично
- ⚠️ Двойной commit в etl/loader.py (один для upload session, другой для транзакций) — может быть оптимизировано

## 5. Фокус сессии
- **Цель:** Завершение Phase 1 и подготовка к production deployment
- **Last Commit:** e506021 — "feat: add auto-period detection for /report command (D-13)" (2026-04-07)
- **Git Status:** Все изменения закоммичены и запушены. Остался нескоммиченный архивный файл docs/tasks/TASK_2026-04-07_ai-verdict-fix.md

### Definition of Done (Phase 1, Task #6 — D-13 auto-period detection)
- [x] Модель UploadSession добавлена в core/models.py
- [x] Таблица upload_sessions создаётся при инициализации БД
- [x] etl/loader.py сохраняет метаданные после загрузки CSV
- [x] api/routers/report.py использует последний upload session при отсутствии периода
- [x] bot/handlers/commands.py поддерживает опциональный параметр /report YYYY-MM
- [x] Автоопределение периода работает корректно
- [x] Изменения закоммичены и запушены в репозиторий

## Следующий шаг
**D-11 CI/CD — ожидает ручных шагов от пользователя**
- [x] GitHub Actions workflow создан (`.github/workflows/deploy.yml`)
- [ ] Пользователь создаёт Doppler Service Token на VPS
- [ ] Пользователь добавляет 4 GitHub Secrets (HOST, USERNAME, SSH_KEY, DEPLOY_PATH)
- [ ] Пользователь клонирует repo на VPS и настраивает Doppler
- [ ] Первый git push → проверить что Actions прошёл зелёным
- [ ] End-to-end тест: CSV → Telegram → отчёт с AI вердиктом
