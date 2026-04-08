# TASK: Phase 2, Task #4 — Integration Smoke Test

**Создан:** 08 апреля 2026, 21:00 (Kyiv)
**Уровень:** L2
**Статус:** pending

## Цель
Выполнить живые проверки на VPS по чеклисту из 7 пунктов, убедиться что Phase 2 работает в production как задумано.

## Scope
Файлы и директории в scope:
- Нет (только проверки на работающей системе)

Вне scope (не трогать):
- Все файлы кода (никаких изменений)
- Исправление найденных багов
- Написание автотестов

---

## Шаги
1. Проверить что контейнеры запущены (`make up`, `make logs`)
2. Выполнить проверку 1: Scheduler стартовал
3. Выполнить проверку 2: GET /health
4. Выполнить проверку 3: GET /observer/anomalies
5. Выполнить проверку 4: GET /observer/trends
6. Выполнить проверку 5: Команды /anomalies и /trends в боте
7. Выполнить проверку 6: Ingest CSV + bounded polling
8. Выполнить проверку 7: Принудительный запуск weekly_digest
9. Составить отчёт по формату (✅ PASS / ⚠️ PARTIAL / ❌ FAIL)
10. Если есть ❌ FAIL — не закрывать задачу, сообщить архитектору

---

## Предусловия

Перед началом убедиться:
- `make up` на VPS прошёл без ошибок
- `make logs` показывает оба контейнера (cfo_api, cfo_bot) запущены
- Doppler: `OWNER_CHAT_ID` установлен

---

## Чеклист проверок

### 1. Scheduler стартовал

```bash
make logs | grep -i "scheduler\|APScheduler\|weekly_digest\|job"
```

Ожидаемый результат: строка вида
`Scheduler started` или `Added job weekly_digest`

Если пусто → scheduler не стартовал, остановиться и сообщить.

---

### 2. GET /health

```bash
curl http://localhost:8002/health
```

Ожидаемый результат: `{"status": "ok"}`

---

### 3. GET /observer/anomalies — базовый ответ

```bash
curl "http://localhost:8002/observer/anomalies"
```

Ожидаемый результат: валидный JSON с полем `detection_status`.
Значение `"insufficient_history"` или `"ok"` — оба корректны на этом этапе.
Значение `"pending"` — допустимо если observer ещё не завершил scan.
Ошибка 500 → остановиться и сообщить.

---

### 4. GET /observer/trends — базовый ответ

```bash
curl "http://localhost:8002/observer/trends?months=3"
```

Ожидаемый результат: валидный JSON с полями `period` и `metrics`.
Пустой `metrics: []` допустим если истории нет.
Ошибка 500 → остановиться и сообщить.

---

### 5. Команды в боте

В Telegram отправить боту:
- `/anomalies` → бот отвечает (любой ответ кроме timeout/ошибки)
- `/trends` → бот отвечает (любой ответ кроме timeout/ошибки)

---

### 6. Ingest CSV + bounded polling

Отправить боту реальный CSV файл.

Проверить последовательность в логах:
```bash
make logs | grep -i "ingest\|observer\|polling\|anomaly\|pending"
```

Ожидаемая последовательность:
1. `ETL completed` (или аналог)
2. `create_task` / observer запущен
3. Polling попытки (1-3)
4. Либо `anomaly alert sent` либо тихое завершение

Если polling не виден в логах → сообщить как Observation.

---

### 7. Принудительный запуск weekly_digest

Одноразовый вызов функции дайджеста напрямую через Python:

```bash
docker exec cfo_bot python3 -c "
import asyncio
from bot.scheduler import weekly_digest
from bot.main import bot
import os
chat_id = int(os.getenv('OWNER_CHAT_ID'))
asyncio.run(weekly_digest(bot, chat_id))
"
```

Ожидаемый результат: сообщение пришло в Telegram.
Проверить: формат читаемый, нет traceback в логах.

---

## Definition of Done

- [ ] Scheduler стартовал, job `weekly_digest` виден в логах
- [ ] GET /health возвращает 200
- [ ] GET /observer/anomalies возвращает валидный JSON
- [ ] GET /observer/trends возвращает валидный JSON
- [ ] /anomalies и /trends в боте отвечают без ошибок
- [ ] После ingest CSV observer отрабатывает (виден в логах)
- [ ] weekly_digest доставлен в Telegram принудительным вызовом

---

## Формат отчёта

Для каждой проверки указать:
- ✅ PASS — работает как ожидалось
- ⚠️ PARTIAL — работает но есть отклонение (описать)
- ❌ FAIL — не работает (приложить лог)

Если есть ❌ FAIL → не закрывать задачу, сообщить архитектору.

---

## Out of Scope

- Написание автотестов (pytest) — отдельная задача если понадобится
- Исправление найденных багов в рамках этой задачи — только фиксация
- Изменения в коде любого рода

## Observations outside scope
*(Engineer заполняет в конце — наблюдения вне scope, не применённые)*