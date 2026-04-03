# TASK: CFO Brain — Phase 1, Task #1
# Scaffold + ETL Pipeline

Created: 2026-04-03
Status: READY TO CODE
Session type: BUILD

---

## Scope

Реализовать минимальный рабочий pipeline:
CSV отправлен в Telegram → распарсен → сохранён в SQLite → подтверждение боту.

AI вердикт и /report — Task #2 (следующая сессия).

---

## Files to create (строго этот список)

### 1. core/config.py
- `Settings(BaseSettings)` с полями:
  - `telegram_token: str`
  - `db_url: str = "sqlite:///./cfo.db"`
  - `openrouter_api_key: str | None = None`
- `get_settings()` с `@lru_cache`

### 2. core/models.py
- SQLAlchemy Base
- Таблица `transactions`:
  - `id` (PK, autoincrement)
  - `date` (Date, not null)
  - `description` (str)
  - `amount` (Decimal/Float)
  - `currency` (str, default "UAH")
  - `category` (str | None)
  - `account` (str | None)
  - `source_file` (str) — имя CSV из которого загружено
  - `created_at` (DateTime, default now)
- Уникальный constraint: `(date, amount, account, description)` — защита от дублей

### 3. core/database.py
- `engine` из `db_url`
- `SessionLocal` factory
- `init_db()` — создаёт таблицы если нет
- `get_db()` — dependency для FastAPI

### 4. etl/parser.py
- `parse_csv(file_bytes: bytes, filename: str) -> list[TransactionRaw]`
- `TransactionRaw` — pydantic модель (date, description, amount, currency, account, category, is_transfer)
- Колонки (точные имена из CSV): `Date`, `Description`, `Category`, `Payee`, `Tag`, `Account`, `Transfer Account`, `Amount`
- Дата: `dateutil.parser.parse(date_str)` → добавить python-dateutil в requirements.txt
- Amount: `str.replace(" ", "").replace(",", ".")` → `float`
- Перевод: если `Transfer Account != ""` → `is_transfer=True`, не грузить в transactions
- Currency mapping: загружает `accounts.yml`, проставляет currency по Account
  - Если account не найден в маппинге → `loguru.warning`, currency = "UNKNOWN", не падать
- Обработать: кодировка UTF-8/CP1251, разделитель `,` или `;`
- `try/except` с `loguru` на каждую строку — битые строки логируются, не валятся

### 5. etl/loader.py
- `load_transactions(rows: list[TransactionRaw], db: Session) -> LoadResult`
- `LoadResult` — pydantic: `inserted: int`, `skipped_duplicates: int`, `errors: int`
- INSERT OR IGNORE по уникальному constraint

### 6. api/routers/ingest.py
- `POST /ingest/csv`
- Accept: `UploadFile`
- Call: `parse_csv` → `load_transactions`
- Return: `LoadResult` as JSON

### 7. api/main.py
- FastAPI app
- Include router: `ingest`
- `@app.on_event("startup")` → `init_db()`
- Health: `GET /health` → `{"status": "ok"}`

### 8. bot/handlers/csv_upload.py
- Handler: `Document` filter (`.csv` extension)
- Download file → POST к `http://cfo_api:8000/ingest/csv`
- Reply: `✅ Загружено: {inserted} транзакций. Дублей пропущено: {skipped}.`
- На ошибку API: `❌ Ошибка обработки файла. Попробуй ещё раз.`

### 9. bot/handlers/commands.py
- `/start` → приветствие + инструкция отправить CSV
- `/status` → `GET /health` → статус API

### 10. bot/main.py
- aiogram `Bot` + `Dispatcher`
- `TOKEN` из `get_settings().telegram_token`
- Register handlers
- `asyncio.run(dp.start_polling(bot))`

### 11. docker-compose.yml
```yaml
services:
  cfo_api:
    build: .
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000
    volumes:
      - ./data:/app/data
    env_file: .env   # Doppler inject → .env на VPS

  cfo_bot:
    build: .
    command: python -m bot.main
    depends_on:
      - cfo_api
    env_file: .env
```

### 12. Makefile
```makefile
up:
    docker compose up -d

down:
    docker compose down

logs:
    docker compose logs -f

build:
    docker compose build

dev-api:
    uvicorn api.main:app --reload --port 8000

dev-bot:
    python -m bot.main
```

### 13. requirements.txt
aiogram==3.7.0
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy==2.0.30
pydantic==2.7.1
pydantic-settings==2.2.1
loguru==0.7.2
python-multipart==0.0.9
httpx==0.27.0
python-dateutil==2.9.0
pyyaml==6.0.1

### 14. accounts.yml
```yaml
# Human-editable mapping of account names to currencies
# New accounts must be added here manually
accounts:
  Payoneer: USD
  IBKR: USD
  "Моно 8235": UAH
  Наличные: UAH
  # Add new accounts as needed
```

### 15. .gitignore
*.db
.env
.env
pycache/
.pyc
.doppler

---

## Definition of Done (Task #1)

- [ ] `make dev-api` стартует без ошибок
- [ ] `POST /ingest/csv` принимает тестовый CSV → возвращает `LoadResult`
- [ ] Дубли не вставляются при повторной отправке того же файла
- [ ] Бот запускается, принимает `.csv` файл, отвечает LoadResult
- [ ] `/start` и `/status` работают
- [ ] `make up` поднимает оба сервиса в Docker

---

## Out of scope (Task #2)

- AI вердикт (analytics/ai_verdict.py)
- /report команда и aggregator.py
- STRATEGY.md парсинг
- analytics_snapshots таблица
- GitHub Actions deploy.yml

---

## Red Flags для агента

- Не трогать STRATEGY.md и HARD.md — только создать шаблоны
- Не делать git commit / push
- Не добавлять Streamlit / дашборд
- Не трогать portfolio_positions, fifo_log — это Фаза 3