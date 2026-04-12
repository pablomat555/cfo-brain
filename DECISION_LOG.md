# DECISION LOG: CFO Brain
> Создан: 2026-04-03
> Статус: Architecture Phase — активен
> Следующий шаг: scaffold repo → Фаза 1

---

## D-01 — Концепция: что такое CFO Brain

**Проблема:**
Личные финансы и инвестиции разбросаны по источникам (CSV из iPhone, Delta, Bybit, IBKR).
Нет единой системы которая видит полную картину, предупреждает и даёт рекомендации.

**Решение:**
CFO Brain — не чат-бот и не трекер. Это оркестратор финансовых решений с тремя режимами:

```
АНАЛИТИК     — что было        (CSV → отчёт + AI вердикт)
НАБЛЮДАТЕЛЬ  — что происходит  (тренды, аномалии, вопросы по истории)
СТРАТЕГ      — что делать      (портфель, ребаланс, симуляция, Red Team)
```

**Принципы работы (из research):**
- Непрерывность: аудит при каждом обновлении данных
- Отсутствие эмпатии: директива "Отклонено" — высшая форма заботы о ликвидности
- Доказательность: любое утверждение подкреплено конкретной транзакцией или индикатором
- Ориентация на ROI: знаменатель — деньги + время + когнитивный ресурс

**Вывод:** CFO Brain — единственная точка доступа к финансовой реальности.
Интерфейс: Telegram. Архитектура: агентная, модульная.

---

## D-02 — Стек технологий

**Проблема:**
Voice Assistant v3.8 работает на n8n + JS. deal-tracker написан на Python.
Нужно решить: единый стек или гибрид.

**Решение: гибридная архитектура**

| Слой | Технология | Обоснование |
|---|---|---|
| Transport / Orchestration | n8n | Уже работает в v3.8, переписывать нет смысла |
| Analytics / Portfolio engine | Python 3.11+ FastAPI | FIFO логика, агрегации, симуляция — JS не справится |
| Telegram gateway | aiogram (Python) | Единый стек с аналитикой |
| База данных | SQLite → PostgreSQL | SQLite для старта, миграция по необходимости |
| Secrets | Doppler | Единый стандарт с openclaw-server |
| Deploy | Docker Compose + GitHub Actions | DEV_PROTOCOL v1.3 |

**Вывод:** n8n остаётся для ETL pipeline (Модуль 1). Python — для всего нового.
Два сервиса в одном docker-compose: `cfo_bot` + `cfo_api`.

---

## D-03 — Data Model

**Проблема:**
v3.8 использовал Markdown файлы как БД — потеряны при переносе.
deal-tracker использовал Google Sheets — потолок при росте и неудобно для агрегаций.

**Решение: SQLite с data model из deal-tracker**

Таблицы (переносим из deal-tracker, меняем хранилище):

```
transactions        — все расходы/доходы из CSV (бывший Core_Trades)
portfolio_positions — открытые позиции (Open_Positions)
fund_movements      — переводы между счетами (Fund_Movements)
account_balances    — балансы по счетам (Account_Balances)
fifo_log            — FIFO расчёты для крипто (Fifo_Log)
analytics_snapshots — сохранённые аналитические срезы
```

Human-editable конфиг (файлы в repo, не в БД):
```
STRATEGY.md  — финансовая стратегия, лимиты, аллокации, цели
HARD.md      — активы на начало периода (обновляется вручную раз в месяц)
```

**Вывод:** SQLite на старте. STRATEGY.md и HARD.md — в repo, версионируются с кодом.
PostgreSQL — только при появлении нескольких пользователей или >100k строк.

---

## D-04 — Источники данных по портфелю

**Проблема:**
Прямые API бирж (Bybit, IBKR) — трудности с подключением, rate limits, auth.
Delta — хорошее приложение, нет публичного API для экспорта.

**Решение: ручной CSV/JSON экспорт как основной источник на Фазах 1-2**

| Фаза | Источник | Механизм |
|---|---|---|
| 1-2 | iPhone app CSV | Отправка файла боту в Telegram |
| 1-2 | Delta export | Ручной экспорт → отправка боту |
| 3 | CCXT (Bybit, Binance) | Автообновление цен (из deal-tracker) |
| 3+ | IBKR API / Payoneer API | MCP интеграция |

**Вывод:** deal-tracker уже имеет CCXT интеграцию — переиспользуем в Фазе 3.
До тех пор: ручной экспорт из Delta — основной workflow.
Delta можно отключить когда deal-tracker engine стабилен (Фаза 3).

---

## D-05 — Что переиспользовать из существующих проектов

**Из Voice Assistant v3.8:**

| Компонент | Статус | Решение |
|---|---|---|
| L1/L2/L3/L4 архитектура слоёв | ✅ работает | Переиспользовать как паттерн |
| Semantic router (AI, не regex) | ✅ работает | Взять в cfo_bot |
| L2.5 JSON Sanitizer | ✅ работает | Взять если LLM в pipeline |
| CSV parser (Debit & Credit формат) | ✅ работает | Переиспользовать полностью |
| Net Savings / investment keywords | ✅ работает | Переиспользовать логику |
| AI вердикт (LLM + STRATEGY.md) | ✅ паттерн верный | Реализовать в Python |
| Force Metadata (chat_id) | ✅ работает | Взять если voice/vision |
| Monobank FX | ❌ не нужен | CSV уже в нужной валюте |
| Ручной ввод транзакций | ❌ не нужен | Есть iPhone приложение |

**Из deal-tracker v1.1:**

| Компонент | Статус | Решение |
|---|---|---|
| Data model (6 таблиц) | ✅ зрелая | Переносим в SQLite |
| FIFO PNL логика | ✅ написана и проверена | Переиспользовать полностью |
| price_updater.py (CCXT) | ✅ работает | Фаза 3 |
| dashboard_utils.py | ✅ аналитические функции | Переиспользовать |
| Google Sheets как БД | ❌ потолок | Заменить на SQLite |
| pm2 | ❌ не наш стандарт | Заменить на Docker Compose |
| Streamlit UI | ❌ не нужен на MVP | Telegram как единственный интерфейс |

---

## D-06 — Модуль 3: Стратег и Sounding Board

**Проблема:**
"Гибкая стратегия + ребаланс + симуляция" — размытый scope.
Нужно определить конкретную архитектуру до реализации.

**Решение: два под-режима внутри Модуля 3**

**CFO Стратег** — работает с STRATEGY.md как источником правил:
- Burn Rate / Runway расчёт по формулам из research
- Аллокация: сравнение факта с целевыми % в STRATEGY.md
- Ребаланс: "ETF недовес на 8%, рекомендую докупить X при следующем пополнении"
- Симуляция: "если доход упадёт на 30% — runway 4 месяца, рекомендую сократить категорию Y"

**Sounding Board** — Red Team режим, активируется явно:
- Триггер: пользователь описывает идею или план
- Агент активирует 4 роли: конкурент / регулятор / скептик / AML офицер
- Каждая роль атакует идею по своему вектору
- Результат: прагматичный вердикт без эмпатии

**AML блок** (обязательный для Украины):
- Лимиты НБУ 2025-2026 (P2P до 100k грн/мес без подтверждённого дохода)
- Красные флаги: структурирование, round-tripping, географический риск
- Флагирование до совершения действия, не после

**STRATEGY.md структура (минимальная):**
```markdown
## Аллокация капитала
- Кэш / ликвидность: X%
- ETF (VOO/VTI): X%
- Крипто: X%

## Лимиты
- Burn Rate лимит: $X/мес
- Emergency fund: X мес расходов

## Стратегия роста
- Тип: Оборонительный рост
- Приоритет ребаланса: [правила]

## Цели
- [горизонт]: [цель]
```

**Вывод:** Sounding Board — отдельный режим, не фоновая функция.
Пользователь явно запрашивает Red Team анализ. Агент не навязывает критику.

---

## D-07 — Связь с openclaw-server

**Проблема:**
Два бота или один — архитектурное решение с долгосрочными последствиями.

**Решение: отдельный бот на Фазах 1-3**

Вариант A (выбран): CFO Brain — отдельный Telegram токен, отдельный сервис.
- Полная изоляция логики и данных
- Независимый деплой
- Нет зависимости от openclaw-server стабильности

Интеграция через OpenClaw routing — рассмотреть после того как оба сервиса
стабильны минимум 1 месяц в production.

**Вывод:** отдельный бот. Единая VPS, разные контейнеры.

---

## D-08 — Фазовый план

### Фаза 1 — АНАЛИТИК (MVP)
**Scope:**
- Telegram бот принимает CSV (формат Debit & Credit)
- ETL парсинг (из v3.8, переписать на Python)
- Сохранение в SQLite таблицу `transactions`
- AI вердикт: LLM получает агрегированный JSON + STRATEGY.md
- Команды: `/report`, `/status`
- Отчёт в Telegram + сохранение в Obsidian через Second Brain save API

**Definition of Done Фазы 1:**
- [ ] CSV отправлен → отчёт получен в Telegram
- [ ] Транзакции сохранены в SQLite
- [ ] AI вердикт сравнивает с STRATEGY.md
- [ ] STRATEGY.md заполнен реальными данными
- [ ] Docker Compose деплой на VPS работает

### Фаза 2 — НАБЛЮДАТЕЛЬ
**Scope:**
- История транзакций накоплена (минимум 2-3 месяца)
- Произвольные вопросы: "как трачу на еду последние 3 месяца?"
- Аномалии: резкий рост категории → предупреждение
- Тренды: burn rate по месяцам, savings rate динамика

### Фаза 3 — СТРАТЕГ
**Scope:**
- Portfolio engine из deal-tracker (SQLite вместо Google Sheets)
- FIFO PNL для крипто позиций
- Ребаланс по STRATEGY.md
- Runway / Burn Rate симуляция
- Sounding Board режим
- CCXT для автообновления цен (из deal-tracker)
- AML блок

### Фаза 4+ — ИНТЕГРАЦИИ
- IBKR API через MCP
- Payoneer API
- Прямые API бирж
- Опционально: OpenClaw routing

---

## D-09 — PeriodReport вместо MonthlyReport

**Проблема:**
Эндпоинт `/report/monthly` и модель `MonthlyReport` семантически ограничивают использование только месячными периодами. CFO Brain должен поддерживать произвольные периоды (неделя, квартал, год, custom range).

**Решение:**
1. Переименовать эндпоинт `/report/monthly` → `/report/period`
2. Переименовать модель `MonthlyReport` → `PeriodReport`
3. Добавить поле `period_type: str` с допустимыми значениями:
   - `"custom"` — произвольный диапазон дат
   - `"this_month"` — все транзакции текущего месяца
   - `"previous_month"` — все транзакции предыдущего месяца
4. Логика определения `period_type` реализуется в `analytics/aggregator.py` на основе дат транзакций
5. Функция `build_monthly_report` переименовывается в `build_period_report`

**Обоснование:**
- Универсальность: один эндпоинт для всех типов отчётов
- Ясность: `period_type` явно указывает характер периода
- Обратная совместимость: существующие вызовы с месячным диапазоном автоматически получат `period_type="this_month"` или `"previous_month"`

**Дата решения:** 2026-04-04
**Статус:** Реализовано в Task #2 Phase 1

---

## D-10 — Verdict Engine: Capital State + Decision Types

**Дата:** 2026-04-05
**Статус:** ✅ ПРИНЯТО

**Проблема:**
Текущая модель verdict engine использует только burn rate из STRATEGY.md.
Это даёт некорректные DENIED при наличии достаточного капитала.

Пример:
burn_rate_limit = $1,500
расход = $3,000 (стоматология)
капитал = $100k+
→ текущая система: DENIED
→ ожидаемое: APPROVED WITH IMPACT

**Решение:**

Два входа в verdict engine:
- STRATEGY.md — правила (doctrine, limits, exception policy)
- Capital State — фактическое состояние (approximate, из account_balances)

**Архитектура verdict engine:**
expense_type (опциональный, default=routine)
    ↓
policy selection (Routine / Strategic / Exceptional)
    ↓
Capital State check (account_balances, approximate)
    ↓
Liquidity impact check
    ↓
APPROVED / APPROVED WITH IMPACT / DENIED

**Три типа решений:**
- routine — обычные расходы, проверка по burn rate
- strategic — инвестиции, проверка по аллокации и ликвидности
- exceptional — медицина, форс-мажор, проверка по ликвидности без burn rate лимита

**Capital State:**
- Хранится в таблице account_balances
- Обновляется при каждом /ingest/csv
- Approximate — точность до доллара не гарантируется и не требуется
- В вердикте показывать с тильдой и датой: ~$4,800 (last updated: 2026-04-04)

**expense_type:**
- Опциональный параметр API
- Default: routine (консервативный fallback)
- Если не передан — система использует routine
- Auto-detection не является частью основного контракта
- Может быть добавлен позже как internal hint

**Exception Policy:**
- Добавить как обязательный блок в STRATEGY.md
- Содержит: список допустимых Exceptional категорий,
  условия одобрения (не ломает ликвидность, не становится паттерном),
  требование фиксации отдельно

**Вывод:**
CFO Brain — фильтр решений, не аналитическая система.
Verdict engine проверяет решения по правилам с учётом состояния капитала.
Контроль важнее анализа.

---

## D-11 — CI/CD Pipeline: GitHub Actions + Doppler + VPS

**Дата:** 2026-04-05
**Статус:** ✅ ПРИНЯТО

**Проблема:**
Ручной деплой CFO Brain на VPS после каждого изменения кода — трудоёмко и подвержено ошибкам.
Нет автоматической проверки что код работает перед деплоем.

**Решение:**
Автоматический CI/CD pipeline на GitHub Actions с деплоем на VPS через SSH и инжекцией секретов через Doppler.

**Архитектура pipeline:**

```
GitHub push → GitHub Actions (ubuntu-latest) → SSH на VPS →
git pull --ff-only → doppler run → docker compose up -d --build
```

**Компоненты:**

1. **GitHub Actions workflow** (`.github/workflows/deploy.yml`):
   - Триггер: push в main ветку или manual trigger
   - Job: deploy с environment production
   - Шаги: checkout, SSH setup, deploy via SSH, verify

2. **GitHub Secrets** (4 секрета):
   - `HOST` — VPS hostname/IP
   - `USERNAME` — SSH username
   - `SSH_KEY` — приватный SSH ключ
   - `DEPLOY_PATH` — путь к директории проекта на VPS

3. **Doppler integration:**
   - Токен Doppler уже настроен на VPS через `doppler configure set token`
   - В deployment команде: `doppler run --project cfo-brain --config prd -- docker compose up -d --build`
   - Секреты инжектируются как environment variables в docker-compose

4. **VPS подготовка:**
   - Клонирован репозиторий
   - Установлен Docker и Docker Compose
   - Настроен Doppler CLI с токеном
   - SSH ключ добавлен в authorized_keys

**Безопасность:**
- Никакие секреты не хардкодятся в код или Dockerfile
- Doppler token хранится только на VPS, не в GitHub Secrets
- SSH ключ хранится как GitHub Secret с минимальными правами
- `git pull --ff-only` гарантирует что история не переписывается

**Ручные шаги для пользователя:**
1. Создать Doppler Service Token на VPS
2. Добавить 4 GitHub Secrets в репозитории
3. Клонировать repo на VPS и настроить Doppler
4. Первый git push → проверить что Actions прошёл зелёным
5. End-to-end тест: CSV → Telegram → отчёт с AI вердиктом

**Вывод:**
Автоматический pipeline устраняет ручной деплой, обеспечивает consistency и позволяет быстро откатываться через git revert.
Doppler как единый источник секретов соответствует архитектурному стандарту проекта.

## D-12 — Порт cfo_api: 8002

**Дата:** 2026-04-05
**Статус:** ✅ РЕАЛИЗОВАНО

**Проблема:** Порт 8000 занят openclaw-server, порт 8001 занят second_brain_mcp.

**Решение:** cfo_api работает на порту 8002.
Стандарт для новых проектов: проверять занятые порты командой
`docker ps --format "table {{.Names}}\t{{.Ports}}"` перед выбором порта.

---

## D-13 — Автоопределение периода для /report

**Дата:** 2026-04-07
**Статус:** ✅ РЕАЛИЗОВАНО

**Проблема:** /report всегда показывал текущий месяц — не совпадало с периодом загруженного CSV.

**Решение:**
- Таблица upload_sessions сохраняет min_date/max_date каждого CSV
- /report без параметров → берёт период последнего upload session
- /report YYYY-MM → явное указание месяца
- Fallback на текущий месяц если upload sessions нет

---

## D-14 — Мультивалютная агрегация

**Дата:** 2026-04-07
**Статус:** ✅ РЕАЛИЗОВАНО

**Проблема:** Агрегатор складывал UAH и USD в одну сумму — цифры бессмысленны.

**Решение:**
- /report запрашивает курс USD/UAH у пользователя
- Пользователь вводит курс (например 43.85) → единый отчёт в USD
- /skip → раздельный отчёт UAH/USD без конвертации
- Курс действует только в рамках одного отчёта, не сохраняется
- В отчёте и verdict payload курс помечается как manual

**Три условия зафиксированы:**
1. Курс ручной — не сохраняется между сессиями
2. /skip обязателен как альтернативный путь
3. rate_type: "manual" явно указывается в payload

---

## D-15 — Analytics Layer Separation

**Дата:** 2026-04-08
**Статус:** ✅ ПРИНЯТО

**Проблема:**
Phase 1 analytics (`aggregator.py`) работает только on-demand: запрос → агрегация из raw transactions → ответ.
Для НАБЛЮДАТЕЛЬ нужна персистентная аналитическая история — сравнение периодов, тренды, baseline для аномалий.
On-demand агрегация каждый раз по raw данным не масштабируется и не даёт исторического контекста.

**Решение:**
Разделить аналитику на два слоя:

```
Layer 1 (Raw):        transactions table — source of truth, не трогать
Layer 2 (Computed):   monthly_metrics, category_metrics, anomaly_events — персистентные агрегаты
```

Layer 2 заполняется хуком после каждого `/ingest/csv` (см. D-21).
Все эндпоинты НАБЛЮДАТЕЛЬ читают только из Layer 2 — быстро, без пересчёта.

**Принцип:**
- Raw данные неизменны — append-only
- Computed метрики перезаписываются при каждом ingest (upsert по month_key)
- Архитектурная граница: `analytics/` не импортирует из `etl/` напрямую

---

## D-16 — Metrics Storage Schema

**Дата:** 2026-04-08
**Статус:** ✅ ПРИНЯТО

**Проблема:**
Нужно определить схему таблиц для персистентных метрик до начала имплементации.

**Решение: три таблицы**

```sql
-- Агрегаты по месяцу (один ряд на месяц)
CREATE TABLE monthly_metrics (
    id           INTEGER PRIMARY KEY,
    month_key    TEXT NOT NULL UNIQUE,  -- 'YYYY-MM'
    total_spent  REAL NOT NULL,         -- всегда в USD
    total_income REAL NOT NULL,         -- всегда в USD
    savings_rate REAL NOT NULL,         -- (income - spent) / income
    burn_rate    REAL NOT NULL,         -- total_spent в USD (по курсу ingest)
    currency     TEXT NOT NULL DEFAULT 'USD',  -- всегда 'USD'; 'multi' запрещён
    fx_rate      REAL NOT NULL,         -- курс UAH/USD применённый при ingest (0.0 если /skip)
    rate_type    TEXT NOT NULL,         -- 'manual' | 'skip'
    tx_count     INTEGER NOT NULL,
    updated_at   TEXT NOT NULL          -- ISO datetime последнего пересчёта
);

-- Агрегаты по категории внутри месяца
CREATE TABLE category_metrics (
    id           INTEGER PRIMARY KEY,
    month_key    TEXT NOT NULL,         -- FK → monthly_metrics.month_key
    category     TEXT NOT NULL,
    total        REAL NOT NULL,         -- в USD (конвертировано по fx_rate месяца)
    tx_count     INTEGER NOT NULL,
    UNIQUE(month_key, category)
);

-- Зафиксированные аномалии
CREATE TABLE anomaly_events (
    id           INTEGER PRIMARY KEY,
    month_key    TEXT NOT NULL,
    category     TEXT NOT NULL,
    current_val  REAL NOT NULL,         -- в USD
    baseline_val REAL NOT NULL,         -- среднее за 3 предыдущих месяца, в USD
    delta_pct    REAL NOT NULL,         -- (current - baseline) / baseline * 100
    threshold    REAL NOT NULL,         -- порог срабатывания (default: 50%)
    status       TEXT NOT NULL,         -- 'new' | 'notified' | 'dismissed'
    detected_at  TEXT NOT NULL
);
```

**Индексы:**
```sql
CREATE INDEX idx_category_metrics_month ON category_metrics(month_key);
CREATE INDEX idx_anomaly_events_month   ON anomaly_events(month_key);
CREATE INDEX idx_anomaly_events_status  ON anomaly_events(status);
```

**FX consistency rule (критично):**
- Все суммы в `monthly_metrics` и `category_metrics` хранятся в USD
- Конвертация происходит один раз — в момент ingest, по курсу введённому пользователем
- `fx_rate` фиксируется вместе с метриками — исторические данные не пересчитываются никогда
- При `/skip`: `fx_rate = 0.0`, `rate_type = 'skip'` — метрики не сопоставимы с USD-периодами,
  аномалия детекция для таких месяцев отключена (`detection_status = 'skip_mode'`)
- `/trends` включает `rate_type` в каждой точке — клиент видит несовместимые периоды явно

**Вывод:**
Три таблицы покрывают все эндпоинты Phase 2 MVP.
`anomaly_events.status` позволяет боту не дублировать уведомления.
FX фиксируется при ingest — исторические метрики иммутабельны.

---

## D-17 — Observer Engine: Spike Detection Logic

**Дата:** 2026-04-08
**Статус:** ✅ ПРИНЯТО

**Проблема:**
Нужно определить точную логику детекции аномалий до имплементации,
чтобы избежать ложных срабатываний на короткой истории.

**Решение:**

**Baseline:**
- Считать по последним 3 полным месяцам относительно анализируемого периода
- Текущий анализируемый месяц в baseline НЕ входит
- Если истории < 3 месяцев → статус `insufficient_history`, алерт не генерируется

**Алгоритм (для каждой категории):**
```
baseline_avg = AVG(category_metrics.total WHERE month_key IN last_3_complete_months)

# Guard: пропустить если baseline невалиден
if baseline_avg is None or baseline_avg <= 0:
    skip → detection_status = 'insufficient_history'

delta_pct = (current_month_total - baseline_avg) / baseline_avg * 100

if delta_pct > threshold (default 50%):
    INSERT INTO anomaly_events (status='new')
```

**Порог:**
- Default: 50% превышение baseline
- Не конфигурируется через API в Phase 2 MVP (hardcoded константа)
- Выносится в конфигурацию в Phase 3

**Условия детекции:**
- Только категории с baseline_avg > $10 (фильтр шума на мелких категориях)
- Только расходные транзакции (не доход)
- Дедупликация: если аномалия для (month_key, category) уже существует — upsert, не дубль

**Статусы anomaly_events:**
- `new` — обнаружена, уведомление ещё не отправлено
- `notified` — бот отправил алерт пользователю
- `dismissed` — пользователь подтвердил / проигнорировал (Phase 3)

---

## D-18 — ОТЛОЖЕНО: /insights/query (NLP Interface)

**Дата:** 2026-04-08
**Статус:** ⏸ ОТЛОЖЕНО — не входит в Phase 2 MVP

**Причина отсрочки:**
- Требует накопленной истории для качественных ответов
- NLP/query parser добавляет сложность без достаточной ценности на старте
- Phase 2 MVP строится на детерминированной логике (SQL-first)

**Зафиксировано для Phase 3:**
- Эндпоинт `/insights/query` с natural language интерфейсом
- Команда `/ask` в боте
- Frequency anomaly detection
- Semantic routing запросов

---

## D-19 — API Endpoints: /anomalies + /trends

**Дата:** 2026-04-08
**Статус:** ✅ ПРИНЯТО

**Проблема:**
Определить контракт новых эндпоинтов до начала имплементации.

**Решение:**

### GET /anomalies
```
Query params:
  month_key: str (optional, default: последний полный месяц)
  status:    str (optional, default: 'new')

Response:
{
  "month_key": "2026-03",
  "anomalies": [
    {
      "category":     "Restaurants",
      "current_val":  450.0,
      "baseline_val": 120.0,
      "delta_pct":    275.0,
      "status":       "new",
      "detected_at":  "2026-04-08T10:00:00Z"
    }
  ],
  "detection_status": "ok" | "insufficient_history"
}
```

### GET /trends
```
Query params:
  months: int (optional, default: 3, max: 12)

Response:
{
  "period": ["2026-01", "2026-02", "2026-03"],   -- ASC сортировка, всегда
  "metrics": [
    {
      "month_key":    "2026-01",
      "burn_rate":    1340.50,
      "savings_rate": 0.18,
      "total_spent":  1340.50,
      "total_income": 1635.00,
      "currency":     "USD",
      "rate_type":    "manual" | "skip"   -- клиент видит несовместимые периоды явно
    },
    ...
  ]
}
```

**Гарантии:**
- Сортировка: всегда ASC по `month_key`
- Если данных за месяц нет — месяц пропускается (не null-запись)
- `rate_type: "skip"` означает мультивалютный период — несопоставим с USD-периодами

**Принципы:**
- Оба эндпоинта читают только из Layer 2 (D-15) — нет пересчёта по raw данным
- Детерминированный вывод, без LLM
- `/trends` в Phase 2 MVP не интерпретирует данные — только структурированный summary

---

## D-20 — Scheduler: бот владеет расписанием, API владеет логикой

**Дата:** 2026-04-08
**Статус:** ✅ ПРИНЯТО

**Проблема:**
Нужно определить где живёт scheduled observer (еженедельный дайджест, проактивные алерты)
без нарушения разделения ответственности bot/api.

**Решение: Scheduler в боте, бизнес-логика в API**

```
cfo_bot (APScheduler):
  - владеет расписанием (cron)
  - вызывает только API endpoints: GET /anomalies, GET /trends
  - форматирует и отправляет Telegram сообщение
  - НЕ содержит аналитической логики

cfo_api:
  - владеет детекцией аномалий, агрегацией трендов
  - НЕ инициирует пуш в Telegram
  - НЕ знает о существовании бота
```

**Расписание Phase 2 MVP:**
- Еженедельный дайджест: понедельник 09:00 (timezone пользователя)
- Post-ingest алерт: немедленно после `/ingest/csv` если есть `new` аномалии

**Библиотека:** `APScheduler 3.x` (AsyncIOScheduler для совместимости с aiogram)

**Вывод:**
Бот остаётся тупым gateway. Scheduler — это транспортный слой, не аналитический.
Архитектурная граница сохраняется: bot знает как доставить, api знает что сказать.

---

## D-21 — Post-Ingest Hook: metrics recalculation trigger

**Дата:** 2026-04-08
**Статус:** ✅ ПРИНЯТО

**Проблема:**
Layer 2 метрики (D-15, D-16) должны обновляться после каждого `/ingest/csv`.
Нужно определить механизм без усложнения ETL pipeline.

**Решение: fire-and-forget hook через asyncio.create_task**

```python
# api/routers/ingest.py (после успешного ETL)
@router.post("/ingest/csv")
async def ingest_csv(...):
    result = await etl_pipeline.run(file)          # существующий ETL — блокирующий

    # Observer hooks: не блокируют ответ клиенту
    asyncio.create_task(
        _run_observer(result.month_key)
    )

    return IngestResponse(
        transactions_loaded=result.count,
        month_key=result.month_key,
        metrics_updated=True,          # задача запущена, не завершена
        detection_status="pending"     # см. GET /anomalies для результата
    )

async def _run_observer(month_key: str) -> None:
    try:
        await metrics_service.recalculate(month_key)
        await anomaly_service.scan(month_key)
    except Exception as e:
        logger.warning(f"Observer failed for {month_key}: {e}")
```

**Почему create_task, не await:**
- ETL уже занял несколько секунд — пользователь ждёт
- recalculate + scan — фоновая работа, результат читается через `/anomalies`
- Telegram не должен висеть на аналитике

**Порядок выполнения:**
1. ETL pipeline — парсинг и загрузка в `transactions` (синхронно, блокирует)
2. `create_task(_run_observer)` — запускает фоновую задачу, не ждёт
3. Ответ клиенту — немедленно после ETL
4. Фоново: `recalculate` → `scan` → результаты в БД

**Обработка ошибок:**
- Observer падает тихо — только WARNING в логах
- ETL результат возвращается в любом случае
- Пользователь получает ответ о загрузке транзакций немедленно

**Ingest response (финальная схема):**
```json
{
  "transactions_loaded": 142,
  "month_key": "2026-03",
  "metrics_updated": true,
  "detection_status": "pending"
}
```

Результаты аномалий — только через `GET /anomalies`.
Бот после ingest может вызвать `/anomalies` через ~2с и уведомить если `anomaly_count > 0`.

---

## Открытые вопросы (не блокируют Фазу 1)

| Вопрос | Когда решать |
|---|---|
| Exception Policy в STRATEGY.md | До реализации verdict engine (Phase 1 deploy) |
| Threshold для Sounding Board триггера | До Фазы 3 |
| Формат экспорта из Delta | До Фазы 2 |
| Нужен ли отдельный `/rebalance` workflow | До Фазы 3 |

## D-22 — Known Limitation: get_last_complete_month()

**Дата:** 2026-04-08
**Статус:** ✅ ЗАКРЫТО в Task #3

**Проблема:**
Текущая реализация `get_last_complete_month()` использует `timedelta(30)`.
На границах месяцев (например 31 марта) возвращает неверный месяц —
scheduler и `/anomalies` будут работать с неправильным периодом.

**Правильная реализация:**
```python
from dateutil.relativedelta import relativedelta
return date.today().replace(day=1) - relativedelta(months=1)
```

**Где исправить:** `api/routers/observer.py` или утилитная функция в `core/`

**Когда исправить:** начало Task #3, до подключения scheduler

---

## D-23 — Post-Ingest Alert: Bot-Side Bounded Polling

**Дата:** 2026-04-08
**Статус:** ✅ ПРИНЯТО

**Проблема:**
После `/ingest/csv` observer hook отрабатывает асинхронно (`create_task`, D-21).
Бот получает `detection_status: "pending"` — аномалии ещё не посчитаны.
Нужен механизм доставки алерта без блокировки ingest endpoint и без нарушения D-21.

**Решение: bounded polling на стороне бота**

```
1. Бот отправляет CSV → получает detection_status: "pending"
2. Бот запускает polling: GET /anomalies?month_key=...&status=new
3. Если detection_status == "pending" → ждёт 2с, повторяет
4. Максимум 3 попытки
5. Если detection_status != "pending" → обрабатывает результат:
   - anomalies непустой → отправляет alert пользователю
   - anomalies пустой  → молча завершает flow
```

**Маркер готовности API:**
`GET /anomalies` возвращает явный `detection_status`:
```json
{
  "month_key": "2026-03",
  "anomalies": [],
  "detection_status": "pending" | "ok" | "insufficient_history" | "skip_mode"
}
```
Бот останавливает polling на любом статусе кроме `"pending"`.
Никаких эвристик по `updated_at` или косвенным признакам.

**Почему не Вариант B (синхронный observer):**
- Нарушает D-21: ingest не должен ждать observer
- Telegram не должен висеть на аналитике
- Observer должен работать фоново

**Контракт polling (финальный):**
> Post-ingest alert delivery uses bounded polling from bot to API:
> 3 attempts, 2s interval, stop on `detection_status != "pending"`

---

## D-24 — Persistent SQLite Volume

**Дата:** 2026-04-08
**Статус:** ✅ РЕАЛИЗОВАНО в Phase 2, Task #7

**Проблема:** SQLite база данных сбрасывалась при каждом редеплое — данные терялись.

**Решение:** Named Docker volume `cfo_data` для `/app/data`.
Данные переживают `docker compose down` и редеплои через CI/CD.

---

## D-25 — Known Limitation: Negative Baseline for Expense Categories

**Дата:** 2026-04-08
**Статус:** ⚠️ ОТКРЫТО — Phase 3

**Проблема:**
Расходы хранятся как отрицательные числа в `transactions`.
При расчёте baseline_avg для аномалий — baseline_avg <= 0, срабатывает guard в D-17
и детекция пропускается (`insufficient_history`).

**Решение (Phase 3):**
При загрузке в `category_metrics` брать `ABS(total)` для расходных категорий.
Или нормализовать знак в ETL на этапе загрузки.

**Не блокирует Phase 3 старт.**

---

## D-26 — Dual Input Model for Capital State

**Дата:** 11 апреля 2026
**Статус:** ✅ ПРИНЯТО

**Проблема:**
`Debit & Credit.csv` описывает поток денег, но не даёт достоверный снимок капитала.
Реконструировать Capital State из transaction history — хрупко и даёт ложную точность.

**Решение: двухконтурная модель данных**

| Контур | Источник | Назначение |
|---|---|---|
| Flow | `Debit & Credit.csv` | transactions, /report, trends, anomalies |
| State | Capital Snapshot CSV/JSON | account_balances, portfolio_positions, /capital |

**Принцип:** Flow отвечает "что происходило", State отвечает "чем владею сейчас".

**Схемы данных:**

`account_balances`: account_name, balance, currency, fx_rate, bucket, as_of_date, source

`portfolio_positions`: account_name, asset_symbol, asset_type, quantity, market_value, currency, liquidity_bucket, fx_rate, as_of_date, source

**Bucket-модель:**
- Bucket аккаунта: грубая классификация (liquid / semi_liquid / investment)
- liquidity_bucket актива: точная классификация внутри аккаунта
- Решает проблему IBKR: один аккаунт, но cash → liquid, IGLD → semi_liquid, VOO → investment

**Task #1 Phase 3 разделён на:**
- Task #1A — Capital Snapshot MVP: ingest account_balances, GET /capital/state, /capital
- Task #1B — Portfolio Breakdown: ingest portfolio_positions, IBKR breakdown, allocation

**Жёсткие ограничения MVP (не делаем):**
- Реконструкция позиций по истории транзакций
- IBKR API / CCXT auto-sync
- Rebalance logic, runway simulation, AI interpretation

**Ingest формат:** CSV — ручной ввод. Telegram wizard — основной UX (см. D-29).

---

## D-27 — FX Rate: Snapshot-Bound Storage

**Дата:** 11 апреля 2026
**Статус:** ✅ ПРИНЯТО

**Проблема:**
Где хранить курс валюты для конвертации в USD при расчёте net worth.
Варианты: accounts.yml, параметр API, колонка в snapshot.

**Решение:**
`fx_rate` — обязательная колонка в snapshot, хранится в БД вместе с записью.

**Правила:**
- USD / USDT → fx_rate = 1.0
- UAH → указывается явно на момент snapshot
- accounts.yml остаётся справочником account→currency, без рыночных курсов
- GET /capital/state читает уже сохранённый fx_rate, не пересчитывает задним числом
- API не принимает fx_rate как параметр запроса

**Причина:**
Historical capital state должен быть воспроизводим. Курс фиксируется в момент snapshot.
Если брать курс из внешнего источника задним числом — capital state становится плавающим.

**Upsert policy:**
По (account_name, as_of_date). Повторная загрузка за ту же дату перезаписывает запись.
Один актуальный снимок на дату, без неоднозначности.

---

## D-28 — UI Portability: API-First Architecture

**Дата:** 11 апреля 2026
**Статус:** ✅ ПРИНЯТО

**Проблема:**
Риск превратить Telegram wizard в "настоящую систему", а API — в придаток.
Нужно зафиксировать границы до начала реализации Phase 3.

**Решение: Telegram-first, not Telegram-bound**

Граница ответственности:
```
Bot/FSM  → собирает поля, подтверждение, вызывает API, форматирует ответ
API      → вся бизнес-логика (FX, bucket classification, upsert policy, aggregation)
DB       → source of truth
```

**Запрет переносить в bot/FSM:**
- FX rules
- bucket classification
- upsert policy
- capital state calculation
- aggregation logic

**Следствие:**
В будущем web/desktop/mobile UI работает с теми же endpoints без переписывания domain logic.
API возвращает структурированный JSON, не Telegram-specific текст.

**API операции (мыслить в этих терминах, не в командах бота):**
- POST /ingest/capital_snapshot
- GET /capital/state
- POST /capital/account
- PATCH /capital/account/{id}
- GET /capital/accounts

---

## D-29 — Capital Snapshot UX: Telegram Wizard as Primary Interface

**Дата:** 11 апреля 2026
**Статус:** ✅ ПРИНЯТО

**Проблема:**
CSV как основной UX для ввода капитала — высокий friction, ошибки, тормозит использование.

**Решение:**
Основной интерфейс — Telegram wizard (aiogram FSM).

**Команды (обязательны в Task #1A):**
- /capital — показать состояние капитала
- /capital_add — добавить счёт (wizard)
- /capital_edit — изменить счёт (wizard)

**Flow /capital_add:**
```
account_name → balance → currency →
(если не USD/USDT → fx_rate) → bucket → confirm → POST /capital/account
```

**Поведение:**
- as_of_date = today (по умолчанию, без запроса у пользователя)
- fx_rate запрашивается только для не-USD/USDT валют
- confirm экран перед сохранением
- Bot вызывает API, не содержит бизнес-логики (D-28)

**CSV роль в системе:**
- bulk import (10+ счетов), тестирование, восстановление данных
- НЕ основной UX

**Scope Task #1A (обновление):**
Bot layer обязателен в MVP: /capital, /capital_add, /capital_edit через aiogram FSM.

---

## D-30 — Single Source Rule for Capital State

**Дата:** 11 апреля 2026
**Статус:** ✅ ПРИНЯТО

**Проблема:**
`account_balances` и `portfolio_positions` могут одновременно содержать стоимость
одного и того же счёта → задвоение net worth в `/capital/state`.

**Решение: приоритет portfolio_positions над account_balances**

Правило для `/capital/state`:
- Если по `account_name` есть записи в `portfolio_positions` за `as_of_date` →
  брать стоимость только из `portfolio_positions`, игнорировать `account_balances`
- Иначе → fallback в `account_balances`

**Уточнение:**
Приоритет применяется в рамках одного `as_of_date`.
Если `portfolio_positions` для `account_name` на эту дату неполны или отсутствуют,
fallback идёт в `account_balances`.

**Разделение ответственности:**
- `account_balances` = верхнеуровневые счета без asset-level разбивки
  (Payoneer, Mono, Cash USD/UAH, Internet card)
- `portfolio_positions` = счета с разбивкой по активам
  (IBKR, Binance, Bybit, Trust Wallet)

Trust Wallet → `portfolio_positions` как одна позиция USDT (единообразно с крипто).

**Совместимость:** Task #1A не переписывается. Task #1B добавляет правило приоритета.

---

## D-31 — Liabilities Model: Receivable vs Liability

**Дата:** 11 апреля 2026
**Статус:** ✅ ПРИНЯТО

**Контекст Task #1B:**
`Loans USD = 1000`, `Loans UAH = 1009` — деньги которые должны мне.

**Правило знаков:**
- `receivable` = мне должны = asset = плюс в net worth
- `liability` = я должен = минус в net worth (не реализовано в MVP)

**Task #1B:**
- Loans USD и Loans UAH → `portfolio_positions`, `type=receivable`, `bucket=illiquid`, знак плюс
- Liabilities (мои долги) — отдельная модель, вне scope Task #1B

---

## Zero-links
---
- [[0 Projects]]
- [[Intelligence OS]]
- [[DECISION_LOG_Architecture_Reset]]
- [[DECISION_LOG_D39_RooCode_Config]]

---
## Links
---
- [[Voice_Assistant_v3_0]]
- https://github.com/pablomat555/deal-tracker
