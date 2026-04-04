# TASK: Переименовать роут /report/monthly → /report/period и класс MonthlyReport → PeriodReport

**Создан:** 2026-04-04
**Уровень:** L2
**Статус:** pending

## Цель
Изменить название роута с `/report/monthly` на `/report/period` и переименовать класс `MonthlyReport` в `PeriodReport` с добавлением поля `period_type: str`. Обеспечить работоспособность всей кодовой базы после переименования.

## Scope
Файлы в scope:
- `api/routers/report.py` — переименовать роут с `/report/monthly` на `/report/period`
- `core/models.py` — переименовать класс `MonthlyReport` → `PeriodReport`, добавить поле `period_type: str`
- `analytics/aggregator.py` — обновить импорт MonthlyReport → PeriodReport
- `core/ai_verdict.py` — обновить импорт MonthlyReport → PeriodReport
- `api/main.py` — проверить импорты, обновить если нужно

Вне scope (не трогать):
- логика агрегации (кроме обновления импортов)
- логика AI вердикта (кроме обновления импортов)
- другие файлы, не использующие MonthlyReport

## Шаги
1. В файле `api/routers/report.py`:
   - Изменить декоратор `@router.get("/monthly")` на `@router.get("/period")`
   - Изменить название функции `get_monthly_report` на `get_period_report`
   - Обновить docstring и комментарии
   - Обновить импорт: `from core.models import MonthlyReport` → `from core.models import PeriodReport`
   - Обновить тип возвращаемого значения: `MonthlyReport` → `PeriodReport`
   - Обновить создание пустого отчёта: `MonthlyReport(...)` → `PeriodReport(...)`

2. В файле `core/models.py`:
   - Переименовать класс `MonthlyReport` в `PeriodReport`
   - Добавить поле `period_type: str` в модель
   - Обновить docstring с описанием класса

3. В файле `analytics/aggregator.py`:
   - Обновить импорт: `from core.models import MonthlyReport` → `from core.models import PeriodReport`
   - Переименовать функцию `build_monthly_report` → `build_period_report` (обязательно)
   - Обновить тип возвращаемого значения в функции `build_period_report`: `MonthlyReport` → `PeriodReport`
   - Обновить все вызовы функции в коде (в `api/routers/report.py`)

4. В файле `core/ai_verdict.py`:
   - Обновить импорт: `from core.models import MonthlyReport` → `from core.models import PeriodReport`
   - Обновить тип параметра в функции `generate_verdict`: `MonthlyReport` → `PeriodReport`

5. Проверить файл `api/main.py` на наличие импортов `MonthlyReport` и обновить их при необходимости.

6. Убедиться что нет других файлов, импортирующих `MonthlyReport` (поиск по кодовой базе).

## Definition of Done
- [ ] Роут `/report/period` доступен в API
- [ ] Класс `PeriodReport` существует с полем `period_type`
- [ ] Импорты во всех файлах обновлены
- [ ] Документация роута обновлена
- [ ] Старый роут `/report/monthly` больше не существует
- [ ] Нет ни одного упоминания MonthlyReport в кодовой базе
- [ ] `make dev-api` запускается без ImportError
- [ ] GET `/report/period` возвращает 200

## Observations outside scope
(Engineer заполняет в конце)