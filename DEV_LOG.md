# DEV LOG: CFO Brain
Последнее обновление: 2026-04-03T18:55:00Z

## Сессия: Phase 1, Task #1 — Scaffold + ETL Pipeline
**Дата:** 2026-04-03  
**Участники:** Orchestrator, Engineer  
**Статус:** ✅ ЗАВЕРШЕНО

### Контекст
- Цель: Создать структуру repo для CFO Brain с dev/prod разделением
- Стек: Python + FastAPI + aiogram 3.x + SQLite + Docker Compose + Doppler
- Фаза: Phase 1 — АНАЛИТИК (MVP)

### Выполненные работы
1. **Структура repo** — созданы все 14+ файлов согласно TASK.md
2. **Core модули** — config.py, models.py, database.py с SQLAlchemy
3. **ETL Pipeline** — parser.py с обработкой non-breaking spaces, loader.py с unique constraint
4. **API** — FastAPI с эндпоинтами /ingest/csv и /health
5. **Bot** — aiogram 3.x с обработкой команд /start, /status и CSV файлов
6. **Docker Compose** — два сервиса (cfo_api, cfo_bot) с healthcheck
7. **Doppler integration** — переменные окружения инжектятся через environment
8. **Makefile** — команды make dev-api, make up, make logs
9. **Конфигурация** — accounts.yml для маппинга аккаунтов на валюты

### Технические детали
- **Unique constraint:** `(date, amount, account, description)` для предотвращения дублей
- **Amount parsing:** Обработка non-breaking space (`\u00a0`) в европейских CSV
- **Currency mapping:** Human-editable YAML файл для добавления новых аккаунтов
- **aiogram 3.x migration:** Полный переход с v2 на v3 (Router pattern, F filters)
- **Doppler compatibility:** Убраны `version` и `env_file` из compose файлов

### Решенные проблемы
1. **ModuleNotFoundError: aiogram.contrib** — миграция на aiogram.fsm.storage.memory
2. **ImportError: ContentTypesFilter** — замена на F.document фильтр
3. **TypeError: Dispatcher constructor** — исправлен вызов Dispatcher(storage=storage)
4. **TokenValidationError** — удален dummy token из docker-compose.override.yml
5. **Healthcheck failed** — заменен curl на Python-based healthcheck
6. **Unclosed connector warning** — некритичное предупреждение aiohttp

### Результаты тестирования
- ✅ `make dev-api` — API поднимается локально
- ✅ `POST /ingest/csv` — принимает CSV, возвращает статистику (4/8 строк загружено, 2 перевода, 2 дубля)
- ✅ `make up` — оба сервиса healthy в Docker Compose
- ✅ Бот запускается — "CFO Brain bot started" в логах
- ✅ Doppler переменные инжектятся корректно

### Observations outside scope (для Task #2)
1. **Unclosed connector warning** — aiohttp сессия не закрывается корректно при старте
2. **Нет AI-анализа** — требуется интеграция с OpenRouter для генерации вердиктов
3. **Нет эндпоинта /report** — нужен для генерации отчётов по транзакциям
4. **Нет категоризации** — транзакции не группируются по категориям

### Следующие шаги
1. **Task #2** — AI вердикт + /report эндпоинт
2. **Git commit** — зафиксировать текущее состояние
3. **Deploy** — развернуть на VPS через GitHub Actions

### Lessons Learned
- **Doppler integration:** Использовать `environment` секцию вместо `env_file`
- **aiogram 3.x:** Router pattern более чистый чем register_message_handler
- **Non-breaking spaces:** Европейские банки используют `\u00a0` как разделитель тысяч
- **Unique constraint:** Нужно включать description для предотвращения ложных дублей

---
**Следующая сессия:** Phase 1, Task #2 — AI вердикт + /report