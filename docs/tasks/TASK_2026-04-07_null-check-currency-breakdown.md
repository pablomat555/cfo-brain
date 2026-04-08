# TASK: Добавить null check для currency_breakdown в core/ai_verdict.py

**Создан:** 2026-04-07T19:39:27Z
**Уровень:** L1
**Статус:** completed

## Цель
Добавить явную проверку на `None` для `currency_breakdown` перед обращением к нему в функции `generate_verdict`.

## Scope
Файлы и директории в scope:
- [`core/ai_verdict.py`](core/ai_verdict.py) — добавление null check для currency_breakdown

Вне scope (не трогать):
- все остальные файлы
- изменения в других частях кода

## Шаги
1. **Найти условие с currency_breakdown в функции generate_verdict**
   - Строка 32: `elif report.rate_type == "split" and report.currency_breakdown:`
   - Строка 34: `for curr, data in report.currency_breakdown.items():`

2. **Изменить условие на явную проверку `is not None`**
   - Заменить `report.currency_breakdown` на `report.currency_breakdown is not None`
   - Также убедиться, что currency_breakdown не пустой словарь (опционально, но можно оставить как есть)

3. **Обновить код**
   ```python
   elif report.rate_type == "split" and report.currency_breakdown is not None:
       currency_info = "Разбивка по валютам:\n"
       for curr, data in report.currency_breakdown.items():
           currency_info += f"- {curr}: доходы {data['total_income']}, расходы {data['total_expenses']}, сбережения {data['net_savings']}\n"
   ```

4. **Выполнить git операции**
   - `git add core/ai_verdict.py`
   - `git commit -m "fix: add explicit null check for currency_breakdown in AI verdict (WAR MODE)"`
   - `git push origin main`

## Definition of Done
- [x] Условие изменено на `report.currency_breakdown is not None`
- [x] Цикл защищён от null
- [x] Изменения закоммичены и запушены

## Observations outside scope
- Файлы `CLAUDE.md` и `TASK.md` были изменены в процессе работы (обновление TASK.md и чтение CLAUDE.md), но не закоммичены, так как не входят в scope.
- Условие `report.currency_breakdown` ранее уже было falsy-проверкой, которая защищала от `None`, но явная проверка `is not None` добавлена для ясности.