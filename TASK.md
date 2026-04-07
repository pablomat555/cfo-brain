# TASK: Update PROJECT_SNAPSHOT.md — обновить секцию "Следующий шаг"

**Создан:** 2026-04-07T20:10:08Z
**Уровень:** L1
**Статус:** pending

## Цель
Обновить секцию "Следующий шаг" в файле [`PROJECT_SNAPSHOT.md`](PROJECT_SNAPSHOT.md) с содержанием, предоставленным пользователем.

## Scope
Файлы и директории в scope:
- [`PROJECT_SNAPSHOT.md`](PROJECT_SNAPSHOT.md)

Вне scope (не трогать):
- все остальные файлы
- другие секции PROJECT_SNAPSHOT.md
- изменения в архитектуре или логике

## Шаги
1. Открыть файл [`PROJECT_SNAPSHOT.md`](PROJECT_SNAPSHOT.md)
2. Найти секцию "Следующий шаг" (строка 77)
3. Заменить текущее содержание секции (строки 77-94) на новое содержание:
```
## Следующий шаг
**Phase 2 — НАБЛЮДАТЕЛЬ (не стартовать до накопления 2-3 месяцев истории)**

### Что выполнено сверх Phase 1 DoD:
- ✅ D-11 CI/CD — GitHub Actions работает, деплой на VPS автоматический
- ✅ D-13 — автоопределение периода из последнего CSV
- ✅ D-14 — мультивалютная агрегация (ручной курс + /skip режим)
- ✅ accounts.yml — 13 аккаунтов с валютами
- ✅ venv311 убран из repo

### Known Issues (некритично):
- ⚠️ Unclosed connector warning в боте (aiohttp cleanup)
- ⚠️ Двойной commit в etl/loader.py

### Открытые решения (не блокируют Phase 2):
- D-10 Exception Policy — добавить в STRATEGY.md
- python3 стандарт — добавить в CLAUDE.md
```
4. Сохранить изменения
5. Выполнить git add PROJECT_SNAPSHOT.md
6. Выполнить git commit с сообщением "docs: update PROJECT_SNAPSHOT with Phase 2 next steps"
7. Выполнить git push

## Definition of Done
- [ ] Секция "Следующий шаг" обновлена с новым содержанием
- [ ] Изменения закоммичены в git
- [ ] Изменения запушены в удалённый репозиторий

## Observations outside scope
(Engineer заполняет в конце - наблюдения вне scope, не применённые)