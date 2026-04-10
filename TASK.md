- бот отвечает: `✅ Загружено: 1680 транзакций`
- в БД остаётся только часть записей (например 433)

Root cause:
- rollback внутри цикла по строкам уничтожает уже вставленные записи
- текущая логика не изолирует обработку одной строки от остальных

---

## Решение

Использовать nested transaction / SAVEPOINT для обработки каждой строки отдельно.

### Требуемый паттерн

Для каждой строки:

```python
with db.begin_nested():
    db.add(transaction)
    db.flush()

Если возникает IntegrityError:

не делать rollback всей внешней транзакции
считать строку дубликатом
продолжать обработку следующих строк
Ожидаемое поведение
дубликат откатывает только текущую строку
ранее успешно вставленные строки сохраняются
commit в конце сохраняет весь батч
inserted отражает реально вставленные строки
skipped_duplicates отражает реально пропущенные дубликаты
Что сделать
Прочитать:
etl/loader.py
при необходимости core/models.py для понимания unique constraint
Исправить цикл загрузки транзакций:
обернуть вставку каждой строки в db.begin_nested()
убрать destructive pattern, где db.rollback() внутри цикла ломает весь batch
сохранить текущую бизнес-логику:
mapping account → currency
UNKNOWN fallback
result.inserted
result.skipped_duplicates
result.errors
Сохранить commit батча в конце функции
Не менять внешний контракт LoadResult, если это не требуется для фикса
Проверить, нет ли второго лишнего/грязного commit-паттерна в этой функции.
Если можно убрать без изменения поведения — убрать.
Если это уже выходит за scope фикса — оставить и отметить в Report.
Definition of Done
 В etl/loader.py больше нет destructive rollback pattern внутри цикла обработки строк
 Для каждой строки используется isolated insert через nested transaction / SAVEPOINT
 Дубликат не откатывает ранее вставленные строки
 python3 -m py_compile etl/loader.py проходит
 После деплоя повторная загрузка CSV сохраняет данные корректно
 Количество записей в transactions соответствует:
старые записи + inserted, а не случайно меньшему числу
 Бот больше не сообщает успешную загрузку при фактической потере вставленных строк
Validation

После apply и деплоя:

Проверить количество строк до загрузки:
docker exec cfo-brain-cfo_api-1 python3 - <<'PY'
import sqlite3
db = sqlite3.connect('/app/data/cfo.db')
cur = db.cursor()
cur.execute("SELECT COUNT(*) FROM transactions")
print(cur.fetchone()[0])
PY
Загрузить CSV через Telegram бота
Проверить количество строк после загрузки:
docker exec cfo-brain-cfo_api-1 python3 - <<'PY'
import sqlite3
db = sqlite3.connect('/app/data/cfo.db')
cur = db.cursor()
cur.execute("SELECT COUNT(*) FROM transactions")
print(cur.fetchone()[0])
PY
Убедиться:
count вырос корректно
нет потери ранее вставленных строк
/trends начинает показывать реальные данные после корректной загрузки / backfill
Out of Scope
Изменения в core/database.py
Изменения пути БД / Docker volume / Doppler
Рефакторинг ETL pipeline
Изменение формата ответа API
Переписывание backfill logic
Любые изменения в metrics_service.py или anomaly_service.py
Режим выполнения

WAR MODE

Только:

read
pinpoint fix
diff
approve
apply
validate

Никаких дополнительных улучшений и рефакторинга вне scope.