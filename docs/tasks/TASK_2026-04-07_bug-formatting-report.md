# TASK: Исправить баг форматирования ответа отчёта в bot/handlers/commands.py

**Создан:** 2026-04-07T19:30:53Z
**Уровень:** L1
**Статус:** completed

## Цель
Исправить падение бота при получении отчёта с currency_breakdown: null и добавить полное логирование traceback.

## Scope
Файлы и директории в scope:
- [`bot/handlers/commands.py`](bot/handlers/commands.py) — добавление traceback logging и защита от null в currency_breakdown

Вне scope (не трогать):
- все остальные файлы
- изменения в API, агрегаторе, моделях

## Шаги
1. **Добавить импорт traceback в начало файла**
   ```python
   import traceback
   ```

2. **Добавить логирование полного traceback в функцию fetch_report**
   - В блоке `except Exception as e:` добавить `traceback.format_exc()`
   - Изменить строку 234 на: `logger.error(f"Error fetching report: {e}\n{traceback.format_exc()}")`

3. **Защитить обращения к currency_breakdown от null в функции format_split_report**
   - Изменить строку 270: вместо `currency_breakdown = report.get("currency_breakdown", {})`
     использовать:
     ```python
     currency_breakdown = report.get("currency_breakdown")
     if currency_breakdown is not None:
         # обрабатываем
     ```
   - Обновить логику: если `currency_breakdown` равен `None` или пустой словарь, показывать общие цифры (как в else блоке)

4. **Также добавить traceback логирование в обработчики исключений cmd_skip_rate и process_rate_input**
   - В строках 119 и 168 добавить `traceback.format_exc()` в лог

5. **Выполнить git операции**
   - `git add bot/handlers/commands.py`
   - `git commit -m "fix: add traceback logging and null-safe currency_breakdown handling (WAR MODE bugfix)"`
   - `git push origin main`

## Definition of Done
- [x] Импорт traceback добавлен
- [x] Логирование полного traceback в fetch_report
- [x] Обращения к currency_breakdown защищены от null
- [x] Логирование traceback в обработчиках исключений
- [x] Изменения закоммичены и запушены

## Observations outside scope
- В файле [`core/ai_verdict.py`](core/ai_verdict.py:32) также есть обращение к `report.currency_breakdown` без проверки на `None`. Это может вызвать ошибку при `currency_breakdown: null`. Однако это вне scope текущей задачи, так как проблема касается только бота.
- Файлы `CLAUDE.md` и `TASK.md` были изменены в процессе работы (обновление TASK.md и чтение CLAUDE.md), но не закоммичены, так как не входят в scope.