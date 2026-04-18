# PROJECT SNAPSHOT: CFO Brain
Последнее обновление: 18 апреля 2026, 19:40 (Kyiv)

## 1. Идентификация
- **Цель:** Персональный финансовый директор в Telegram — трекинг бюджета, анализ расходов, симуляция финансовых сценариев
- **Owner:** Я
- **Repo:** git@github.com:pablomat555/cfo-brain.git
- **Стек:** Python · aiogram 3.x · FastAPI · SQLite · Docker Compose · Doppler
- **Текущая фаза:** Phase 4 АКТИВНА (i18n + runway hotfixes)

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
- **Статус:** Phase 1 ЗАВЕРШЁН, Phase 2 ЗАВЕРШЁН, Phase 3 ЗАВЕРШЁН, Phase 4 АКТИВНА
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
  - Phase 3, Task #1B ✅ ЗАВЕРШЁН (Portfolio Breakdown & Enhanced Capital State — Single Source Rule, asset classification, новые эндпоинты, бот команды)
  - **Дополнительные задачи Phase 2:**
    - ✅ **Volume persistence** — добавлен named volume `cfo_data` для `/app/data`
    - ✅ **Конфигурация CFO_DB_URL** — исправлено поле `cfo_db_url` для использования env переменной
    - ✅ **Backfill скрипт** — создан `scripts/backfill_metrics.py` для обработки отсутствующих месяцев
    - ✅ **Фикс rollback бага** — исправлен деструктивный паттерн в `etl/loader.py` через `db.begin_nested()`
    - ✅ **Валидатор OWNER_CHAT_ID** — добавлен validator для преобразования пустой строки в None
    - ✅ **Фильтрация технических записей** — добавлена фильтрация Balancing transaction и переводов между счетами
  - **Дополнительные задачи Phase 3:**
    - ✅ **Фикс D-25 (отрицательные суммы в baseline)** — исправлена агрегация расходных категорий, backfill 22 месяцев, аномалии детектируются
    - ✅ **Restore FX Rate Request in CSV Upload** — восстановлен запрос курса валют при загрузке CSV с UAH транзакций, добавлен эндпоинт `/ingest/csv/preview`, миграция 005
    - ✅ **Backup стратегия SQLite** — реализована система бэкапов БД cfo.db с автоматическим backup в Backblaze B2 и restore через CLI, добавлены скрипты `backup.py` и `restore.py`, сервис `cfo_backup` в docker-compose, переменные окружения в Doppler, протестировано в production (D-35)
  - Phase 4, Task #1 ✅ ЗАВЕРШЁН (i18n Loader — bot/i18n.py, locales/ru.json+en.json, smoke test PASS, D-36)
  - Phase 4, Task #2 ✅ ЗАВЕРШЁН (i18n Migration: digest, observer, runway, verdict — все хендлеры мигрированы, smoke test PASS, D-36)
  - Phase 4, Task #3 ✅ ЗАВЕРШЁН (/capital_edit Full Wizard — FSM с 4 полями, PATCH /capital/account/{id}, D-37)
  - Phase 4, Task #4 ✅ ЗАВЕРШЁН (/position_edit Full Wizard — FSM с паттернами D-37, PATCH /capital/position/{id}, smoke test PASS, D-38)

### Что работает
- ✅ Полная структура repo создана (20+ файлов)
- ✅ ETL pipeline: парсинг CSV с non-breaking spaces, загрузка в SQLite с isolated transactions через `db.begin_nested()`
- ✅ Фильтрация: Balancing transaction и переводы между счетами пропускаются
- ✅ API: FastAPI с эндпоинтами POST /ingest/csv, GET /health, GET /report/period, GET /observer/anomalies, GET /observer/trends, POST /capital/ingest/capital_snapshot, GET /capital/state, POST /capital/account, GET /capital/accounts, POST /capital/position, GET /capital/positions, GET /ingest/csv/preview
- ✅ Bot: aiogram 3.x, обработка команд /start, /status, /report, /anomalies, /trends, /capital, /capital_add, /capital_edit, /position_add, /positions, /position_edit и CSV файлов с запросом курса для UAH транзакций
- ✅ Docker Compose: два сервиса (cfo_api, cfo_bot) с healthcheck (порт 8002) и named volume `cfo_data`
- ✅ Doppler integration: переменные окружения инжектятся через environment (TELEGRAM_TOKEN, CFO_DB_URL, OWNER_CHAT_ID, OPENROUTER_API_KEY, LOG_LEVEL)
- ✅ **Backup система:** Автоматический backup БД cfo.db в Backblaze B2 через скрипты `backup.py` и `restore.py`, сервис `cfo_backup` в docker-compose, переменные окружения в Doppler, протестировано в production (D-35)
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
- ✅ **Конфигурация CFO_DБ_URL:** Приложение использует env переменную для пути к БД
- ✅ **Backfill скрипт:** `scripts/backfill_metrics.py` обрабатывает отсутствующие месяцы автоматически
- ✅ **Фикс rollback бага:** Изолированные транзакции предотвращают потерю данных при дубликатах
- ✅ **Валидатор OWNER_CHAT_ID:** Преобразование пустой строки в None предотвращает crash бота
- ✅ **Фильтрация технических записей:** Balancing transaction и переводы пропускаются, отчёты показывают реалистичные суммы
- ✅ **Portfolio Breakdown:** Single Source Rule (D-30) реализована — portfolio_positions приоритет над account_balances для одинакового account/date
- ✅ **Asset Classification:** Классификатор `core/capital_classifier.py` маппит символы на asset_type и liquidity_bucket (хардкод)
- ✅ **Enhanced Capital State:** GET /capital/state возвращает breakdown по asset_type и liquidity_bucket, включает illiquid bucket для Loans receivable (D-31)
- ✅ **Portfolio Snapshot CSV:** Поддержка загрузки portfolio snapshot через POST /capital/ingest/capital_snapshot с автоматической классификацией
- ✅ **Bot Commands:** Новые команды /position_add (FSM wizard), /positions (список позиций), /position_edit (stub)
- ✅ **FX Rate Request:** Бот запрашивает курс для UAH транзакций при загрузке CSV, предоставляет опцию /skip, сохраняет rate_type="manual" в monthly_metrics
- ✅ **Verdict Engine:** Детерминированный движок принятия решений POST /verdict → Capital State + STRATEGY.md → APPROVED / APPROVED_WITH_IMPACT / DENIED. Включает три политики (Routine, Strategic, Exceptional), расчёт impact, интеграцию с ботом командой /verdict
- ✅ **Runway Engine:** Burn Rate Calculator + Runway Simulation в analytics/runway_engine.py. Эндпоинты GET /runway и POST /runway/simulate, фильтрация по rate_type="manual", расчёт runway месяцев до emergency floor и нуля, self-sustaining статус при положительном cash flow. Интеграция с ботом командой /runway.
- ✅ **CFO Rules блок в STRATEGY.md:** Machine-readable секция с параметрами стратегии для strategy_loader, парсинг через regex, fallback на defaults с warning
- ✅ **/capital_edit Full Wizard:** FSM с выбором счёта, поля (balance, currency, fx_rate, bucket), PATCH /capital/account/{id}, state.clear() паттерн, prepare_confirm с явным флагом edit, D-37
- ✅ **/position_edit Full Wizard:** FSM с выбором позиции, поля (account_name, asset_symbol, quantity, market_value, currency, fx_rate, as_of_date), PATCH /capital/position/{id}, паттерны D-37, защитная проверка API response (D-38)

### Known Issues
- ⚠️ Unclosed connector warning в боте (aiohttp cleanup) — некритично
- ⚠️ Двойной commit в etl/loader.py (один для upload session, другой для транзакций) — может быть оптимизировано
- ⚠️ APScheduler shutdown hook отсутствует — возможны warnings при docker stop. Phase 3.
- ⚠️ Rate type "skip" используется по умолчанию для исторических данных — аналитика с ним ограничена
- ~~⚠️ `/capital_edit` wizard обновляет только баланс, не другие поля~~ ✅ **ЗАКРЫТ D-37** — полный wizard (balance, currency, fx_rate, bucket) задеплоен и работает (17 апреля 2026)
- ~~⚠️ `/position_edit` требует доработки UI выбора позиции (оставлен stub)~~ ✅ **ЗАКРЫТ D-38** — полный wizard (6 полей) задеплоен и работает (18 апреля 2026)
- ⚠️ `capital_classifier.py` использует хардкод маппинг — конфигурируемость планируется в Phase 4 (D-10 Verdict Engine)

### Recently Closed Issues
- ✅ **D-32 — FX Conversion: Per-Transaction Currency Check** — исправлен баг агрегации доходов (конвертация только UAH транзакций)
- ✅ **savings_rate display fix в scheduler** — убрано умножение на 100, дайджест показывает корректные проценты
- ✅ **/digest команда добавена** — ручной запуск дайджеста через команду бота
- ✅ **Phase 3, Task #3 — Runway / Burn Rate симуляция** — реализован BurnRateCalculator и RunwayEngine, эндпоинты GET /runway и POST /runway/simulate, фильтрация по rate_type="manual", интеграция с ботом командой /runway, добавлена запись D-34
- ✅ **WAR MODE фикс #1 — API_BASE_URL** — `bot/handlers/capital.py` использовал `localhost:8002` вместо `cfo_api:8002`, бот не мог достучаться до API (`All connection attempts failed`). Коммит `0a2df86`.
- ✅ **WAR MODE фикс #2 — Markdown → HTML** — все 8 мест в `capital.py` с `parse_mode="Markdown"` переведены на `parse_mode="HTML"`. Динамические поля (account_name, asset_symbol, liquidity_bucket) содержали символы ломающие Markdown парсер Telegram. Коммит `0b3a61b`.
- ✅ **WAR MODE фикс #3 — field mismatch в /capital** — `format_capital_state` читал поля `balance_usd`/`balance`, API отдаёт `value_usd`/`market_value`. KeyError устранён, добавлен `asset_symbol` в строку для читаемости. Коммит `33931f3`.
- ✅ **Phase 4, Task #2 — i18n Migration: digest, observer, runway, verdict** — добавлены недостающие ключи в locales, мигрированы все оставшиеся хендлеры на `t()` систему, smoke test PASS, DECISION_LOG.md и PROJECT_SNAPSHOT.md обновлены.
- ✅ **WAR MODE — runway parse_mode fix** — убраны `parse_mode="Markdown"` в `runway.py`: `str(e)` ломал Telegram Markdown парсер (`_` в трассировке). Коммит `851a6c2`.
- ✅ **WAR MODE — runway router не зарегистрирован** — `api/main.py` не содержал `runway` в import/include_router. Незакоммиченное изменение. Коммит `bae22dc`.
- ✅ **WAR MODE — runway файлы не в репо** — `api/routers/runway.py` и `analytics/runway_engine.py` были untracked → ImportError на VPS. Коммит `011d114`. Правило добавлено в AGENT.md.
- ✅ **WAR MODE D-37 — /capital_edit FSM полный фикс** — четыре связанных бага: `state.clear()` при старте, `prepare_confirm edit=True/False`, API `/capital/accounts` с id, `PATCH` в `call_api()`. Коммиты `ee11a72`, `289cede`, `50841ff`, `9ae0f64`, `4795a89`. D-37 зафиксирован.
- ✅ **Phase 4, Task #4 — /position_edit Full Wizard** — реализация по паттернам D-37: модели PositionSummary и PositionUpdateRequest, эндпоинты GET /capital/positions и PATCH /capital/position/{id}, локали position_edit, FSM с 6 полями, smoke test PASS. Коммит `fc5472c`.
- ✅ **WAR MODE D-38 — API Response Structure Bug** — `/position_edit` падал с "string indices must be integers, not 'str'". Root cause: API endpoint GET /capital/positions возвращает `{"positions": [...]}`, но бот ожидал raw list. Фикс: `positions = response.get("positions", [])` в `bot/handlers/capital.py`. Коммит `075aa0b`.

## 5. Фокус сессии
- **Цель:** Phase 4, Task #5 — Конфигурируемый Capital Classifier (вынос хардкод маппинга)
- **Last Commit:** `075aa0b` fix(bot): parse API response correctly in position_edit
- **Git Status:** Все изменения закоммичены и запушены, контейнеры работают
- **Состояние VPS:** `/position_edit` wizard работает (FSM с 6 полями), PATCH успешен, все сервисы healthy

## Следующий шаг
**Phase 4 АКТИВНА. Task #4 завершён, Task #5 в очереди.**

**Выполненные действия Phase 4:**
1. ✅ **Task #1 — i18n Loader** — создан `bot/i18n.py`, локали `ru.json`/`en.json`, smoke test PASS
2. ✅ **Task #2 — i18n Migration** — мигрированы все оставшиеся хендлеры (digest, observer, runway, verdict)
3. ✅ **Task #3 — /capital_edit Full Wizard** — FSM с 4 полями, PATCH /capital/account/{id}, фиксы D-37
4. ✅ **Task #4 — /position_edit Full Wizard** — FSM с 6 полями, PATCH /capital/position/{id}, фиксы D-38

**Phase 4, Task #5 — Конфигурируемый Capital Classifier** (текущий приоритет):
- Вынос хардкод маппинга из `core/capital_classifier.py` в конфигурационный файл
- Поддержка динамического обновления через API
- Интеграция с Verdict Engine
- Smoke test на VPS

**Phase 4, Task #6 — Enhanced Observer Alerts** (планируется):
- Уведомления о значительных отклонениях в реальном времени
- Кастомизация порогов через STRATEGY.md

**Статус Phase 4:**
✅ Task #1 — i18n Loader
✅ Task #2 — i18n Migration
✅ Task #3 — /capital_edit Full Wizard
✅ Task #4 — /position_edit Full Wizard
🔶 Task #5 — Конфигурируемый Capital Classifier
⬜ Task #6 — Enhanced Observer Alerts

**Known Issues для Phase 4:**
- ⚠️ `capital_classifier.py` использует хардкод маппинг — будет решено в Task #5
- ⚠️ Unclosed connector warning в боте (aiohttp cleanup) — некритично
- ⚠️ APScheduler shutdown hook отсутствует — возможны warnings при docker stop

## Phase 4, Task #1 — i18n (Internationalization)

Цель: поддержка нескольких языков интерфейса бота.

Scope:
- Вынести все пользовательские строки из bot/handlers/ в locales/
- Структура: locales/ru.json, locales/en.json (старт)
- Простой loader: t("key") → строка по активному языку
- LANGUAGE env var в Doppler для переключения
- Добавить locales/tr.json, locales/de.json по запросу

Предусловие:
- Все новые хендлеры (начиная с Task #2) пишут строки как константы
  вверху файла, не инлайнят в код

Оценка: L2, ~1 день работы

## Phase 4, Task #2 — i18n Migration: digest, observer, runway, verdict

Цель: завершить миграцию всех оставшихся хендлеров на i18n систему.

Scope:
- Добавить недостающие ключи для observer (`api_connect_error`, `invalid_month_format`, `invalid_months_range`, `invalid_parameter`) в `locales/ru.json` и `locales/en.json`
- Мигрировать `bot/handlers/digest.py` (2 строки) — заменить на `t("digest.forming")`, `t("digest.error")`
- Мигрировать `bot/handlers/observer.py` (6 строк) — заменить на `t("observer.anomalies_search")`, `t("observer.trends_analysis")`, `t("observer.api_connect_error")`, `t("observer.invalid_month_format")`, `t("observer.invalid_months_range")`, `t("observer.invalid_parameter")`
- Мигрировать `bot/handlers/runway.py` (14 строк) — удалить блок констант MSG_*, заменить на `t()` вызовы в `_format_runway()`
- Мигрировать `bot/handlers/verdict.py` (12 строк) — удалить блок констант MSG_*, заменить на `t()` вызовы в `cmd_verdict` и `_format_verdict`
- Smoke test команд на VPS: `/digest`, `/anomalies`, `/trends`, `/runway`, `/verdict`
- Обновить DECISION_LOG.md (D-36) и PROJECT_SNAPSHOT.md

Результат:
- ✅ Все пользовательские строки в боте используют `t()` с dot-notation
- ✅ Ключи присутствуют в обоих языках (ru, en)
- ✅ Smoke test (локальный импорт + проверка ключей) PASS
- ✅ DECISION_LOG.md обновлён
- ✅ PROJECT_SNAPSHOT.md обновлён (удалён known issue о неполной миграции)

Статус: ✅ ВЫПОЛНЕНО (16 апреля 2026)
