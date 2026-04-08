# TASK: Добавить Exception Policy в STRATEGY.md (D-10)

**Создан:** 2026-04-08T14:58:46Z
**Уровень:** L1
**Статус:** pending

## Цель
Добавить новый блок "Exception Policy" в конец файла [`STRATEGY.md`](STRATEGY.md) согласно спецификации D-10.

## Scope
Файлы и директории в scope:
- [`STRATEGY.md`](STRATEGY.md)
- [`DEV_LOG.md`](DEV_LOG.md)
- [`PROJECT_SNAPSHOT.md`](PROJECT_SNAPSHOT.md)

Вне scope (не трогать):
- все остальные файлы
- изменение существующих секций STRATEGY.md кроме добавления нового блока
- изменение логики приложения

## Шаги
1. Открыть файл [`STRATEGY.md`](STRATEGY.md)
2. Найти конец файла (после секции "## 5. STRATEGIC GOALS (2026)")
3. Добавить новый блок с содержанием:
```
## Exception Policy
Три типа расходов:
- routine — плановые повторяющиеся расходы (еда, транспорт, коммунальные)
- strategic — запланированные крупные расходы (инвестиции, оборудование)
- exceptional — незапланированные расходы вне лимитов (требуют явного обоснования)

Лимиты для exceptional расходов:
- До $100 — автоматически approved
- $100-$500 — approved with impact (влияет на месячный burn rate)
- Свыше $500 — требует обоснования в момент принятия решения
```
4. Сохранить изменения
5. Обновить [`DEV_LOG.md`](DEV_LOG.md): добавить запись о выполнении задачи D-10
6. Обновить [`PROJECT_SNAPSHOT.md`](PROJECT_SNAPSHOT.md): удалить D-10 из списка "Открытые решения" в секции "Следующий шаг"
7. Выполнить git add STRATEGY.md DEV_LOG.md PROJECT_SNAPSHOT.md
8. Выполнить git commit с сообщением "docs: add Exception Policy (D-10) to STRATEGY.md"
9. Выполнить git push

## Definition of Done
- [ ] Блок "Exception Policy" добавлен в конец STRATEGY.md
- [ ] DEV_LOG.md обновлён с записью о выполнении D-10
- [ ] PROJECT_SNAPSHOT.md обновлён (D-10 удалён из открытых решений)
- [ ] Изменения закоммичены в git
- [ ] Изменения запушены в удалённый репозиторий

## Observations outside scope
(Engineer заполняет в конце - наблюдения вне scope, не применённые)