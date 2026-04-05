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

---

## Открытые вопросы (не блокируют Фазу 1)

| Вопрос | Когда решать |
|---|---|
| Exception Policy в STRATEGY.md | До реализации verdict engine (Phase 1 deploy) |
| Threshold для Sounding Board триггера | До Фазы 3 |
| Формат экспорта из Delta | До Фазы 2 |
| Нужен ли отдельный `/rebalance` workflow | До Фазы 3 |

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
