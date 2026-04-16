# AGENT.md — Agent Contract
# CFO Brain

Всегда отвечай на русском языке.

## Формат дат
- Всегда использовать читаемый формат: `08 апреля 2026, 20:33 (Kyiv)`
- Никогда не использовать ISO 8601 с суффиксом Z (UTC) — только Kyiv timezone
- Применяется везде: PROJECT_SNAPSHOT.md, DEV_LOG.md, TASK.md, DECISION_LOG.md

## Правила
- Читай PROJECT_SNAPSHOT.md и TASK.md перед любым действием
- Сначала план → потом код
- Не выходи за scope TASK.md
- Улучшения вне scope → только в Report секции "Observations outside scope", не в коде
- Никогда не пиши в Vault напрямую — только через MCP или save API
- **Строки в хендлерах:** все пользовательские строки (тексты сообщений боту) выносить как константы вверху файла handler.py. Не инлайнить строки напрямую в send_message() вызовы.
- **Git before VPS deploy:** перед smoke test на VPS всегда запускать `git status` — убедиться что все новые файлы добавлены в коммит. Untracked файлы не попадают в образ Docker. Повторяющийся паттерн провала: файл создан локально, не закоммичен → контейнер собирается без него → 404/ImportError на VPS.

## Файлы проекта (repo) vs Vault

Следующие файлы живут в repo — читать и писать свободно:
- DECISION_LOG.md
- PROJECT_SNAPSHOT.md
- TASK.md
- DEV_LOG.md

Vault (Obsidian) — только через MCP → /save. Это разные вещи. Не путать.

## Проект
- Название: CFO Brain
- Repo: git@github.com:pablomat555/cfo-brain.git
- Стек: Python 3.11+ · FastAPI · aiogram 3.x · SQLite · Docker Compose · Doppler · OpenRouter
- Текущая фаза: Phase 3 АКТИВНА

## Архитектурный контекст
- Паттерн: Telegram → Bot Gateway → CFO Brain API → ETL Pipeline → SQLite → Response
- Аналог по архитектуре: openclaw-server (знакомая структура)
- Second Brain: read-only через HTTP API, не через прямой mount
- Secrets: Doppler (проект: cfo-brain / prd) — никогда не хардкодить
- Локальная разработка: `doppler run -- uvicorn api.main:app --reload --port 8002`
- Если .env нужен исключительно для локального теста — создать вручную, добавить в .gitignore, никогда не коммитить

## Структура репо
```
bot/        — Telegram gateway (aiogram 3.x)
api/        — FastAPI, бизнес-логика, эндпоинты
core/       — модели данных, конфигурация, БД
etl/        — парсинг CSV, загрузка транзакций
data/       — SQLite база данных (cfo.db)
analytics/  — агрегация, метрики, отчёты
scripts/    — утилиты (backfill и др.)
```

## Stack Rules — Python
- Typing: strict. `list[str]`, `dict[str, Any]`, `X | None`
- Logging: `loguru`, не `print()`
- Schemas: `pydantic` для всех моделей данных
- Paths: `pathlib.Path`
- Error handling: `try/except` на всех I/O, network, subprocess
- Всегда использовать `python3` (не `python`)
- Не проверять версию Python перед выполнением команд

## Stack Rules — Docker / DevOps
- Images: pinned versions, никогда `latest` в production
- Secrets: никогда в Dockerfile или docker-compose.yml
- Compose changes: требуют approve
- Deploy: git push → GitHub Actions → VPS Hetzner (DEV_PROTOCOL v1.3)
- Порт API: 8002

## Stack Rules — БД и миграции
- SQLite через SQLAlchemy — использовать `db.begin_nested()` для изолированных транзакций (D-ETL rollback fix)
- Миграции — нумеровать последовательно (001, 002, ...), текущая последняя: 005
- Дубликаты — уникальный constraint (date, amount, account, description)
- Финансовые данные — никогда не удалять, только помечать

## Финансовые правила (критично)
- Single Source Rule (D-30): portfolio_positions приоритет над account_balances для одинакового account/date
- FX конвертация: только UAH транзакции конвертируются, не все подряд (D-32)
- Расходные категории: применять `abs()` при агрегации (D-25 fix)
- Балансирующие транзакции и переводы между счетами — фильтровать, не включать в отчёты
- Capital classifier: `core/capital_classifier.py` — маппинг символов на asset_type и liquidity_bucket

## Smoke Test Protocol

`py_compile` и `ast.parse` — НЕ smoke test. Запрещено засчитывать задачу выполненной на основе проверки синтаксиса.

Минимальный smoke test для Python модуля:
1. Живой импорт: `python3 -c "from module import func"`
2. Для API: `curl http://localhost:8002/health`
3. Для бота: реальная команда в боте (`/start`, `/status`), не только exec в контейнере

Smoke test на VPS обязателен если задача затрагивает:
- `bot/handlers/` (любой файл)
- `docker-compose.yml`
- `core/config.py`

VPS smoke test = реальная команда в боте, не только exec в контейнере.

## Red Flags — остановиться и сообщить
- Задача требует изменений в 5+ несвязанных файлах
- Непонятно как проверить результат
- Конфликт с решением в DECISION_LOG.md
- Запрос на доступ к .env или реальным значениям секретов
- Предложение сделать git commit / push
- Изменения в ETL pipeline без явного тестового сценария
- Изменения в финансовых агрегациях без понимания влияния на исторические данные
- Попытка засчитать `py_compile` / синтаксическую проверку как smoke test → СТОП

## Marp — визуализация

Когда пользователь просит "сделай презентацию" или "визуализируй" —
создавай файл с расширением .md с frontmatter `marp: true`.
Каждый слайд разделяй `---`.
