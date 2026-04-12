# TASK: Phase 3 / Task #1B — Portfolio Breakdown & Enhanced Capital State

**Создан:** 12 апреля 2026, 20:07 (Kyiv)
**Уровень:** L2
**Статус:** pending

## Цель
Расширить Capital Snapshot MVP добавлением детализации по активам (portfolio_positions), реализовать Single Source Rule (D-30), классификацию активов, новые эндпоинты и команды бота.

## Архитектурные правила (обязательны)

**D-30 — Single Source Rule (критично):**
В /capital/state для каждого account_name на конкретный as_of_date:
- Если есть записи в portfolio_positions → берём только оттуда
- Если portfolio_positions отсутствуют или неполны → fallback в account_balances
- Приоритет строго в рамках одного as_of_date. Не смешивать даты.

**D-31 — Loans = receivable = asset (плюс в net worth)**
Loans USD и Loans UAH → portfolio_positions, type=receivable, bucket=illiquid.

**Asset classification (жёстко, не менять)**
- USDT / Trust Wallet USDT → stablecoin → liquid
- Crypto (BTC, ETH, LTC...) → crypto → semi_liquid
- SGOV → bond_etf → semi_liquid
- ETF (VOO, QQQ, VXUS) → etf → investment
- Steam → alternative → semi_liquid
- Loans → receivable → illiquid
- Cash USD/UAH → cash → liquid

**Upsert key**
(account_name, asset_symbol, as_of_date)

**Запрет**
Никакой логики классификации и FX в bot/FSM. Только сбор полей и вызов API.

## Scope

### 1. База данных
- Таблица `portfolio_positions` уже создана (миграция 003). Проверить наличие полей `asset_type` и `liquidity_bucket`.
- При необходимости добавить недостающие колонки через ALTER.

### 2. Классификатор активов
Создать `core/capital_classifier.py` с функцией `classify_asset(symbol: str) -> tuple[asset_type, liquidity_bucket]`.
Логика классификации согласно правилам выше. Использовать в API и bulk ingest.

### 3. API эндпоинты (расширение `api/routers/capital.py`)

**POST /capital/position** — upsert одной позиции
- Body: { account_name, asset_symbol, quantity, market_value, currency, fx_rate, as_of_date, source? }
- Классификация через `classify_asset`
- Upsert по (account_name, asset_symbol, as_of_date)
- Response: { позиция с вычисленными asset_type, liquidity_bucket }

**POST /ingest/capital_snapshot** — расширить поддержку snapshot_type=portfolio
- Парсинг CSV с колонками: account_name, asset_symbol, quantity, market_value, currency, fx_rate, as_of_date
- Применение классификации для каждой строки
- Bulk upsert в portfolio_positions

**GET /capital/positions** — список позиций
- Query params: as_of_date (optional), account_name (optional)
- Возвращает список позиций с пагинацией?

**GET /capital/state** — расширить breakdown
- Добавить в ответ секции:
  - `by_asset_type`: { "stablecoin": total_usd, "crypto": ..., "etf": ..., "receivable": ... }
  - `by_liquidity_bucket`: { "liquid": ..., "semi_liquid": ..., "investment": ..., "illiquid": ... }
- Реализовать Single Source Rule (D-30)

### 4. Bot commands (новые FSM в `bot/handlers/capital.py`)

**/position_add** — wizard для добавления позиции
Шаги:
1. account_name (текст)
2. asset_symbol (текст)
3. quantity (число)
4. market_value (число)
5. currency (кнопки USD/USDT/UAH/EUR/Other)
6. Если не USD/USDT → запросить fx_rate
7. as_of_date (по умолчанию today, можно пропустить)
8. Confirm → POST /capital/position

**/position_edit** — wizard для редактирования позиции
1. GET /capital/positions → показать список позиций (кнопки)
2. Выбор позиции → показать текущие значения
3. Запросить новое quantity / market_value
4. Confirm → POST /capital/position (upsert)

**/positions** — показать список позиций
- GET /capital/positions → форматированный список

### 5. CSV ingest (вспомогательный)
- Создать `fixtures/portfolio_snapshot_example.csv` с примером
- Поддержка в `etl/capital_parser.py`

## Файлы в scope
- `core/models.py` — модели PortfolioPositionCreate, PortfolioPositionResponse, расширение CapitalStateResponse
- `core/capital_classifier.py` — классификатор активов (новый)
- `api/routers/capital.py` — новые эндпоинты, логика Single Source Rule, интеграция классификатора
- `etl/capital_parser.py` — парсинг CSV для portfolio snapshot
- `bot/handlers/capital.py` — новые FSM состояния и хендлеры
- `core/migrations/003_capital_snapshot_tables.sql` — возможно добавить недостающие колонки
- `fixtures/portfolio_snapshot_example.csv` — пример CSV

## Вне scope (не трогать)
- Логика ребаланса, runway, AI verdict
- IBKR API, CCXT auto-sync
- Liabilities (долги) — кроме receivable (Loans)
- Изменение существующих эндпоинтов account_balances (кроме расширения /capital/state)
- Любые файлы вне перечисленных

## Шаги
1. Проверить структуру таблицы portfolio_positions, при необходимости дополнить миграцией.
2. Создать core/capital_classifier.py с classify_asset.
3. Добавить модели Pydantic для позиций в core/models.py.
4. Реализовать POST /capital/position в api/routers/capital.py.
5. Расширить POST /ingest/capital_snapshot для snapshot_type=portfolio.
6. Реализовать GET /capital/positions.
7. Расширить GET /capital/state: Single Source Rule + breakdown by asset_type/liquidity_bucket.
8. Создать FSM состояния и хендлеры для /position_add, /position_edit, /positions в bot/handlers/capital.py.
9. Создать пример CSV.
10. Протестировать интеграцию: добавление позиции → /capital/state показывает корректный breakdown.

## Definition of Done
- [ ] core/capital_classifier.py создан, classify_asset возвращает правильные типы для тестовых символов
- [ ] POST /capital/position работает, upsert по (account_name, asset_symbol, as_of_date)
- [ ] POST /ingest/capital_snapshot с snapshot_type=portfolio загружает CSV в portfolio_positions
- [ ] GET /capital/positions возвращает список позиций с фильтрами
- [ ] GET /capital/state включает breakdown by asset_type и by liquidity_bucket
- [ ] Single Source Rule реализована и протестирована (позиции приоритетнее балансов)
- [ ] Команды /position_add, /position_edit, /positions работают через FSM
- [ ] Бот не содержит логики классификации/FX — только вызовы API
- [ ] fixtures/portfolio_snapshot_example.csv создан

## Observations outside scope
(Engineer заполняет в конце — наблюдения вне scope, не применённые)