# TASK: Исправить конфигурацию для использования CFO_DB_URL

**Создан:** 09 апреля 2026, 22:06 (Kyiv)
**Уровень:** L1
**Статус:** pending

## Цель
Исправить конфигурацию Pydantic Settings для правильного чтения env переменной `CFO_DB_URL`, чтобы приложение писало данные в volume-mounted путь `/app/data/cfo.db`.

## Scope
Файлы и директории в scope:
- `core/config.py` (переименовать поле db_url → cfo_db_url)
- `core/database.py` (обновить использование settings.db_url → settings.cfo_db_url)

Вне scope (не трогать):
- Все остальные файлы
- Docker-compose изменения (уже выполнены)
- Миграция существующих данных

## Шаги
1. Открыть `core/config.py`
2. Переименовать поле `db_url` в `cfo_db_url` с дефолтным значением `"sqlite:////app/data/cfo.db"`
3. Удалить `Field(env="CFO_DB_URL")` (Pydantic Settings v2 автоматически маппит CFO_DB_URL на cfo_db_url)
4. Открыть `core/database.py`
5. Заменить все использования `settings.db_url` на `settings.cfo_db_url`
6. Запушить изменения и дождаться деплоя на VPS
7. Выполнить проверки:
   - Проверка 1: Убедиться что settings.cfo_db_url возвращает правильный путь
   - Проверка 2: Проверить что приложение пишет в `/app/data/cfo.db`
   - Проверка 3: Загрузить тестовые данные через бота
   - Проверка 4: Проверить сохранность данных после редеплоя

## Definition of Done
- [ ] Поле `cfo_db_url` добавлено в `core/config.py` с правильным дефолтным значением
- [ ] Все использования `settings.db_url` заменены на `settings.cfo_db_url`
- [ ] После деплоя `settings.cfo_db_url` возвращает `sqlite:////app/data/cfo.db`
- [ ] Приложение пишет данные в volume-mounted путь
- [ ] Данные сохраняются между редеплоями

## Observations outside scope
(Engineer заполняет в конце)