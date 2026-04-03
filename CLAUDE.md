# CLAUDE.md — Agent Contract
# CFO Brain

Всегда отвечай на русском языке.

## Правила
- Читай PROJECT_SNAPSHOT.md и TASK.md перед любым действием
- Сначала план → потом код
- Не выходи за scope TASK.md
- Улучшения вне scope → только в Report секции "Observations outside scope", не в коде
- Никогда не пиши в Vault напрямую — только через MCP или save API

## Проект
- Название: CFO Brain
- Repo: git@github.com:pablomat555/cfo-brain.git (создать)
- Стек: Python + FastAPI · Telegram Bot (aiogram) · SQLite / PostgreSQL · Docker Compose · Doppler (secrets)

## Архитектурный контекст
- Паттерн: Telegram → Gateway → CFO Brain API → Data Layer
- Аналог по архитектуре: openclaw-server (знакомая структура)
- Second Brain: read-only через HTTP API, не через прямой mount
- Secrets: Doppler, никогда не хардкодить

## Stack Rules — Python
- Typing: strict. `list[str]`, `dict[str, Any]`, `X | None`
- Logging: `loguru`, не `print()`
- Schemas: `pydantic` для всех моделей данных
- Paths: `pathlib.Path`
- Error handling: `try/except` на всех I/O, network, subprocess

## Stack Rules — Docker / DevOps
- Images: pinned versions, никогда `latest` в production
- Secrets: никогда в Dockerfile или docker-compose.yml
- Compose changes: требуют approve
- Deploy: git push → CI/CD → VPS (DEV_PROTOCOL v1.3)

## Red Flags — остановиться и сообщить
- Задача требует изменений в 5+ несвязанных файлах
- Непонятно как проверить результат
- Конфликт с решением в DECISION_LOG.md
- Запрос на доступ к .env или реальным значениям секретов
- Предложение сделать git commit / push
