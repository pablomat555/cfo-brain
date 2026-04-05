# TASK: Изменить порт cfo_api с 8000 на 8001

**Создан:** 2026-04-05
**Уровень:** L2
**Статус:** pending

## Цель
Изменить порт API сервиса cfo_api с 8000 на 8001 во всех конфигурационных файлах и точках обращения к API.

## Scope
Файлы и директории в scope:
- `docker-compose.yml` — изменить порты и health check
- `docker-compose.override.yml` — изменить порты
- `Makefile` — изменить порт в dev-api команде
- `api/main.py` — изменить порт в блоке `if __name__ == "__main__"`
- `bot/handlers/commands.py` — изменить URL health check
- `bot/handlers/csv_upload.py` — изменить URL ingest endpoint
- `.github/workflows/deploy.yml` — изменить health check порт если присутствует

Вне scope (не трогать):
- Все остальные файлы проекта
- Конфигурационные файлы вне перечисленных
- Git операции (commit, push) — выполняются после завершения задачи

## Шаги
1. Изменить `docker-compose.yml`:
   - Строка 4: `--port 8000` → `--port 8001`
   - Строка 14: `"8000:8000"` → `"8001:8001"`
   - Строка 16: `'http://localhost:8000/health'` → `'http://localhost:8001/health'`

2. Изменить `docker-compose.override.yml`:
   - Строка 8: `"8000:8000"` → `"8001:8001"`

3. Изменить `Makefile`:
   - Строка 14: `--port 8000` → `--port 8001`

4. Изменить `api/main.py`:
   - Строка 30: `port=8000` → `port=8001`

5. Изменить `bot/handlers/commands.py`:
   - Строка 33: `"http://cfo_api:8000/health"` → `"http://cfo_api:8001/health"`

6. Изменить `bot/handlers/csv_upload.py`:
   - Строка 27: `"http://cfo_api:8000/ingest/csv"` → `"http://cfo_api:8001/ingest/csv"`

7. Проверить `.github/workflows/deploy.yml` на наличие health check с портом 8000 и изменить на 8001 если присутствует

8. Проверить что нет других упоминаний порта 8000 в коде приложения (исключая vendor файлы)

## Definition of Done
- [ ] Все 7 файлов изменены согласно спецификации
- [ ] Docker Compose поднимается с новым портом (`make up`)
- [ ] API доступен на порту 8001 (`curl localhost:8001/health`)
- [ ] Бот может подключиться к API (`make dev-bot` или через Docker)
- [ ] Health check проходит успешно
- [ ] Изменения закоммичены и запушены в main (после ручного подтверждения)

## Observations outside scope
(Engineer заполняет в конце - наблюдения вне scope, не применённые)