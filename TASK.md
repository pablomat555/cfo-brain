Phase 4, Task #3 — /capital_edit Full Wizard (Rev 4)

SCOPE:

1. core/models.py
   AccountUpdateRequest(BaseModel):
     balance: float | None = None
     currency: str | None = None
     fx_rate: float | None = None
     bucket: str | None = None
     [account_name — отсутствует намеренно, D-37]

   Validator (только payload, не БД):
     Срабатывает только если currency присутствует в payload:
     - currency in (UAH, EUR) and fx_rate is None → raise ValueError
     - currency in (USD, USDT) and fx_rate not in (None, 1.0) → raise ValueError
     Если payload содержит только fx_rate без currency → validator не срабатывает

2. api/routers/capital.py
   PATCH /capital/account/{id}:
     - Нормализация в handler перед сохранением:
         if req.currency in (USD, USDT): req.fx_rate = 1.0
     - Partial update: обновляет только non-None поля
     - 404 если account не найден
     - except IntegrityError → 409 с понятным сообщением
     - Возвращает обновлённую запись

3. bot/handlers/capital.py — EditCapital FSM
   Состояния:
     SelectAccount  — GET /capital/accounts → inline KB
     SelectField    — inline KB: balance | currency | fx_rate | bucket
     InputValue     — currency/bucket: inline KB; balance/fx_rate: текст
     FxRateInput    — условный шаг:
                        показывается при field=currency
                        только для non-USD/USDT валют (UAH, EUR и др.)
                        для USD/USDT — шаг пропускается
                        API нормализует fx_rate=1.0 независимо от FSM
     Confirm        — diff "Было → Станет"
                        при field=currency: fx_rate показывается в diff явно
                        кнопки: ✅ Сохранить / ❌ Отменить

   Cancel:
     /cancel и кнопка ❌ на любом шаге → clear_state

   API вызов:
     Только после ✅ Confirm
     parse_mode="HTML"
     API_BASE_URL = http://cfo_api:8002
     Обработка 409 → показать сообщение пользователю

4. locales/ru.json + en.json
   Ключи: capital.edit.select_account, capital.edit.select_field,
   capital.edit.input_value, capital.edit.input_fx_rate,
   capital.edit.confirm, capital.edit.saved, capital.edit.cancelled,
   capital.edit.not_found, capital.edit.error, capital.edit.conflict

CONSTRAINTS:
- account_name не редактируется (D-37: upsert key, rename = отдельная операция)
- Нормализация fx_rate=1.0 в API handler, не в validator
- Validator проверяет только входной payload, не состояние записи в БД
- IntegrityError → 409 в API handler
- FSM не содержит FX бизнес-правил
- git status перед деплоем
- Smoke test: /capital_edit на VPS, все 4 поля

DEFINITION OF DONE:
- /capital_edit показывает список счетов, 4 редактируемых поля
- При field=currency + non-USD/USDT: FSM показывает шаг FxRateInput
- При field=currency + USD/USDT: шаг FxRateInput пропускается
- API нормализует fx_rate=1.0 для USD/USDT независимо от FSM
- Confirm: полный diff, fx_rate показан явно при смене currency
- API: 422 для UAH/EUR без fx_rate, 409 для IntegrityError, 404 для missing
- Smoke test VPS PASS
- DECISION_LOG.md (D-37) + PROJECT_SNAPSHOT.md обновлены