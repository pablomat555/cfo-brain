# TASK: Phase 3, Task #2 — Verdict Engine
# Date: 14 апреля 2026 (Kyiv)
# Status: READY FOR EXECUTION (v2 — after review fixes)

## Objective
Детерминированный Verdict Engine: POST /verdict → Capital State + STRATEGY.md
→ APPROVED / APPROVED_WITH_IMPACT / DENIED

---

## Files to CREATE

### 1. `core/strategy_loader.py`

```python
class StrategyConfig(BaseModel):
    burn_rate_limit_usd: float = 1500.0
    payoneer_target_usd: float = 5000.0
    sgov_target_usd: float = 5000.0
    min_liquid_reserve: float = 10000.0       # payoneer + sgov, для StrategicPolicy
    monthly_investment_usd: float = 500.0
    emergency_fund_months: int = 3
    exceptional_auto_approved_usd: float = 100.0   # только для impact/reason
    exceptional_with_impact_usd: float = 500.0     # только для impact/reason
```

Парсинг: regex по STRATEGY.md.
ОБЯЗАТЕЛЬНО: try/except вокруг каждого извлечения + fallback на default + logger.warning().
Кешировать при старте приложения (читать файл один раз).

---

### 2. `api/services/verdict_engine.py`

Трёхслойная архитектура:

#### ContextBuilder
Читает из БД (Single Source Rule D-30):
- `liquid_total` — сумма liquid bucket из account_balances + portfolio_positions
- `semi_liquid_total` — crypto bucket
- `investment_total` — ETF bucket
- `total_net_worth` — сумма всего
- `last_updated` — дата последнего capital snapshot (MAX(as_of_date))
- `burn_rate` — последний monthly_metrics.total_expenses (abs)

#### RoutinePolicy
```
if amount <= strategy.burn_rate_limit_usd:
    APPROVED, impact=NONE
elif liquid_total >= amount:
    APPROVED_WITH_IMPACT
else:
    DENIED
```

#### StrategicPolicy
```
liquid_after = liquid_total - amount
if liquid_after >= strategy.min_liquid_reserve:
    APPROVED
elif liquid_after >= strategy.payoneer_target_usd:
    APPROVED_WITH_IMPACT
else:
    DENIED
```

#### ExceptionalPolicy
```
# burn_rate НЕ применяется
if liquid_total >= amount:
    APPROVED_WITH_IMPACT
    # impact/reason определяются через thresholds (не decision):
    # amount <= exceptional_auto_approved_usd → impact=LOW,    reason="auto-approved exceptional"
    # amount <= exceptional_with_impact_usd  → impact=MEDIUM,  reason="exceptional spend"
    # amount >  exceptional_with_impact_usd  → impact=HIGH,    reason="track separately"
else:
    DENIED
```

#### Impact calculation (все политики)
```
ЗАЩИТА: если liquid_total == 0 → impact = "HIGH"
иначе: ratio = amount / liquid_total
    < 5%   → LOW
    5–15%  → MEDIUM
    > 15%  → HIGH
Для APPROVED в RoutinePolicy → impact = "NONE"
```

#### VerdictResponse
```python
class VerdictMeta(BaseModel):
    liquid_before: float
    liquid_after: float
    last_updated: str
    policy_used: str
    expense_type: str

class VerdictResponse(BaseModel):
    decision: Literal["APPROVED", "APPROVED_WITH_IMPACT", "DENIED"]
    reason: str
    impact_level: Literal["NONE", "LOW", "MEDIUM", "HIGH"]
    capital_after: float   # liquid_total - amount
    liquidity_warning: bool  # capital_after < strategy.min_liquid_reserve
    meta: VerdictMeta
```

---

### 3. `api/routers/verdict.py`

```python
class VerdictRequest(BaseModel):
    amount: float
    currency: str = "USD"
    category: str
    description: str = ""
    expense_type: str = "routine"   # routine | strategic | exceptional
    account: str | None = None
```

POST /verdict — последовательность:
```
1. FX normalization:
   if currency == "UAH":
       rate_row = последний monthly_metrics где rate_type == "manual"
       fx_rate = rate_row.fx_rate if rate_row else 42.5  # fallback константа
       logger.warning если использован fallback
       amount_usd = amount / fx_rate
   else:
       amount_usd = amount

2. ctx = ContextBuilder.build(db)
3. strategy = strategy_loader.load()
4. result = DecisionEngine.decide(request с amount_usd, ctx, strategy)
5. return VerdictResponse
```

Если ctx.liquid_total == 0 (capital state пустой):
```
raise HTTPException(400, "Capital State не загружен. Используй /capital_add.")
```

---

### 4. `bot/handlers/verdict.py`
Только форматирование. Никакой логики (D-28).
Язык: русский (единый стандарт бота).

Команда: `/verdict <amount> <category> [expense_type]`

Примеры:
```
/verdict 500 стоматология exceptional
/verdict 1500 инвестиции strategic
/verdict 200 продукты
```

Формат ответа:
```
💡 Вердикт: APPROVED WITH IMPACT

📋 Категория: стоматология (exceptional)
💵 Сумма: $500

📊 Ликвидность до: ~$8,420
📊 Ликвидность после: ~$7,920
⚠️ Impact: MEDIUM (5.9%)
🔔 Предупреждение о ликвидности: нет

📅 Capital snapshot: 13 апр 2026
```

Если 400 от API (capital state пустой):
```
⚠️ Capital State не загружен. Используй /capital_add.
```

---

## Files to MODIFY

### 5. `api/main.py`
```python
from api.routers.verdict import router as verdict_router
app.include_router(verdict_router, prefix="/api/v1")
```

### 6. `bot/main.py`
Зарегистрировать verdict handler.

---

## Migration
Не требуется. Читаем существующие таблицы.

---

## Test Scenarios

```bash
# 1. Routine — approved (< burn_rate_limit)
POST /verdict {"amount": 200, "currency": "USD", "category": "продукты", "expense_type": "routine"}
# Ожидаем: APPROVED, impact=NONE

# 2. Routine — approved with impact (> burn_rate_limit, liquid есть)
POST /verdict {"amount": 2000, "currency": "USD", "category": "техника", "expense_type": "routine"}
# Ожидаем: APPROVED_WITH_IMPACT

# 3. Exceptional — не блокируется burn rate
POST /verdict {"amount": 3000, "currency": "USD", "category": "медицина", "expense_type": "exceptional"}
# Ожидаем: APPROVED_WITH_IMPACT, impact=HIGH

# 4. Exceptional — маленькая сумма, impact=LOW
POST /verdict {"amount": 50, "currency": "USD", "category": "лекарства", "expense_type": "exceptional"}
# Ожидаем: APPROVED_WITH_IMPACT, impact=LOW

# 5. Strategic — liquid floor check
POST /verdict {"amount": 15000, "currency": "USD", "category": "крипто", "expense_type": "strategic"}
# Ожидаем: зависит от capital state (DENIED если liquid_after < $5k)

# 6. UAH normalization
POST /verdict {"amount": 21250, "currency": "UAH", "category": "продукты", "expense_type": "routine"}
# Ожидаем: нормализация → $500, далее routine logic

# 7. Capital state пустой
POST /verdict {"amount": 100, "currency": "USD", "category": "test"}
# Ожидаем: 400 + сообщение
```

---

## Definition of Done
- [ ] POST /verdict возвращает корректный VerdictResponse
- [ ] RoutinePolicy: burn_rate_limit без AND liquid
- [ ] ExceptionalPolicy: burn_rate НЕ применяется
- [ ] StrategicPolicy: liquid floor = strategy.min_liquid_reserve
- [ ] impact_level = amount/liquid_total (защита от division by zero)
- [ ] liquidity_warning = capital_after < min_liquid_reserve
- [ ] UAH нормализуется через manual fx_rate или fallback 42.5
- [ ] capital state пустой → 400 с объяснением
- [ ] /verdict команда в боте работает

---

## Critical Rules
1. Вся логика только в verdict_engine.py — не в боте (D-28)
2. Capital State читать через Single Source Rule (D-30)
3. Не читать raw transactions для capital state
4. Значения из STRATEGY.md только через strategy_loader (с fallback)

---

## DECISION_LOG — добавить запись D-33

```
## D-33 — Verdict Engine v2: Three-Policy Architecture
Дата: 14 апреля 2026 (Kyiv)
Статус: ✅ ПРИНЯТО

Три политики: Routine / Strategic / Exceptional.
ContextBuilder — переиспользуемый слой (Task #3 Runway будет использовать его).
strategy_loader.py парсит STRATEGY.md — числа не хардкодятся в коде.
RoutinePolicy: burn_rate = месячный агрегат, не лимит на транзакцию.
ExceptionalPolicy: thresholds только для impact/reason, не для decision.
Strategic liquid floor = strategy.min_liquid_reserve ($10k).
liquidity_warning = capital_after < min_liquid_reserve.
FX fallback = 42.5 с logger.warning если manual rate недоступен.
Язык бота: русский — единый стандарт для всех handlers.
```
