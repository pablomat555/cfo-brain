# TASK: Phase 3 / Task #1A — Capital Snapshot MVP

**Создан:** 11 апреля 2026
**Завершён:** 11 апреля 2026
**Уровень:** L2
**Статус:** completed

## Цель
Минимальный надёжный источник истины для состояния капитала.
Flow (transactions) ≠ State (snapshot). Контуры не смешивать.

## Архитектурные правила (обязательны)
- D-26: Dual Input Model — snapshot отдельный контур от transactions
- D-27: fx_rate хранится в snapshot, не вычисляется задним числом
- D-28: Bot/FSM только собирает поля и вызывает API. Вся логика в API.
- D-29: Telegram wizard — основной UX. CSV — вспомогательный.

## Scope

### 1. DB Schema

Таблица `account_balances`:
| Поле | Тип | Примечание |
|---|---|---|
| id | int PK | |
| account_name | str | |
| balance | float | |
| currency | str | |
| fx_rate | float | 1.0 для USD/USDT |
| bucket | str | liquid / semi_liquid / investment |
| as_of_date | date | |
| source | str | manual / csv |
| created_at | datetime | |
| updated_at | datetime | upsert обновляет это поле |

Таблица `portfolio_positions` — создать структуру, данные в Task #1B:
| Поле | Тип |
|---|---|
| id | int PK |
| account_name | str |
| asset_symbol | str |
| asset_type | str |
| quantity | float |
| market_value | float |
| currency | str |
| fx_rate | float |
| liquidity_bucket | str |
| as_of_date | date |
| source | str |
| created_at | datetime |

Upsert: по (account_name, as_of_date). Повторная загрузка перезаписывает.

### 2. API endpoints

**POST /ingest/capital_snapshot**
- multipart/form-data: file (CSV), snapshot_type (account | portfolio)
- Парсинг → upsert в соответствующую таблицу
- Response:
```json
{
  "rows_loaded": 4,
  "snapshot_type": "account",
  "as_of_date": "2026-04-11",
  "accounts": ["Payoneer", "Monobank UAH", "Bybit", "IBKR"]
}
```

**GET /capital/state**
- Query param: as_of_date (optional, default: latest available)
- Логика: читает account_balances → считает balance * fx_rate для USD → группирует по bucket
- Response:
```json
{
  "as_of_date": "2026-04-11",
  "total_net_worth_usd": 56305.0,
  "by_bucket": {
    "liquid": {
      "total_usd": 8305.0,
      "accounts": [
        {"account_name": "Payoneer", "balance": 4200, "currency": "USD", "balance_usd": 4200},
        {"account_name": "Monobank UAH", "balance": 180000, "currency": "UAH", "fx_rate": 43.85, "balance_usd": 4105}
      ]
    },
    "semi_liquid": { "total_usd": 3500.0, "accounts": [...] },
    "investment": { "total_usd": 42000.0, "accounts": [...] }
  }
}
```

**POST /capital/account** (single record upsert, для wizard)
- Body: { account_name, balance, currency, fx_rate, bucket, as_of_date }
- Upsert по (account_name, as_of_date)
- Response: { account_name, balance_usd, as_of_date }

**GET /capital/accounts**
- Возвращает список уникальных account_name из account_balances
- Нужен для /capital_edit — показать список для выбора

### 3. Bot commands (aiogram FSM)

**/capital**
- GET /capital/state → форматировать:
💼 Capital State (11 апр 2026)
Net Worth: $56,305
💧 Liquid: $8,305
• Payoneer: $4,200
• Monobank: $4,105 (₴180,000 @ 43.85)
🔄 Semi-liquid: $3,500
• Bybit: $3,500
📈 Investment: $42,000
• IBKR: $42,000
- Если нет данных: "Нет снимка капитала. Используй /capital_add"

**/capital_add** (FSM wizard)
Шаги:
1. Запросить account_name (текстом)
2. Запросить balance (число)
3. Запросить currency (кнопки: USD / USDT / UAH / EUR / Other)
4. Если не USD/USDT → запросить fx_rate ("Курс к USD?")
5. Запросить bucket (кнопки: 💧 Liquid / 🔄 Semi-liquid / 📈 Investment)
6. Confirm экран: показать введённые данные + кнопки "✅ Сохранить" / "❌ Отмена"
7. POST /capital/account → сообщение об успехе

**/capital_edit** (FSM wizard)
Шаги:
1. GET /capital/accounts → показать список кнопок
2. Пользователь выбирает account
3. Показать текущие данные + запросить новый balance
4. Confirm → POST /capital/account (upsert перезапишет)

### 4. CSV ingest (вспомогательный)

Формат account_snapshot.csv:
account_name,balance,currency,fx_rate,bucket,as_of_date,source
Payoneer,4200,USD,1.0,liquid,2026-04-11,manual
Monobank UAH,180000,UAH,43.85,liquid,2026-04-11,manual
Bybit,3500,USD,1.0,semi_liquid,2026-04-11,manual
IBKR,42000,USD,1.0,investment,2026-04-11,manual

Добавить в repo: `fixtures/capital_snapshot_example.csv`

## Out of Scope
- portfolio_positions данные (структура создаётся, данные — Task #1B)
- IBKR API, CCXT
- Rebalance / runway / AI verdict
- UI вне Telegram

## Definition of Done
- [x] account_balances и portfolio_positions таблицы созданы
- [x] POST /ingest/capital_snapshot принимает account CSV
- [x] POST /capital/account принимает single record
- [x] GET /capital/state возвращает net worth + breakdown by bucket
- [x] GET /capital/accounts возвращает список счетов
- [x] /capital показывает snapshot
- [x] /capital_add wizard сохраняет через API
- [x] /capital_edit wizard обновляет через API
- [x] Тест: /capital_add 4 счёта → /capital → net worth корректный
- [x] fixtures/capital_snapshot_example.csv в repo