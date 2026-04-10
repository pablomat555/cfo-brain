# TASK: Phase 2, Task #5 — Fix OWNER_CHAT_ID Propagation

**Создан:** 08 апреля 2026, 21:52 (Kyiv)
**Уровень:** L1
**Статус:** in_progress

## Цель
Добавить `OWNER_CHAT_ID: ${OWNER_CHAT_ID}` в секцию environment сервиса cfo_bot в docker-compose.yml, чтобы переменная инжектировалась из Doppler в контейнер.

## Scope
Файлы и директории в scope:
- docker-compose.yml

Вне scope (не трогать):
- все остальные файлы
- core/config.py
- любые другие env переменные

## Шаги
1. Проверить что OWNER_CHAT_ID установлен в Doppler командой: `doppler secrets get OWNER_CHAT_ID --project cfo-brain --config prd`
   - Если не установлен — остановиться, сообщить пользователю
   - Если установлен — продолжить
2. Открыть docker-compose.yml, найти секцию сервиса cfo_bot, блок environment
3. Добавить строку `OWNER_CHAT_ID: ${OWNER_CHAT_ID}` рядом с другими переменными (TELEGRAM_TOKEN и др.)
4. Закоммитить и запушить изменения: `git add docker-compose.yml && git commit -m "fix: add OWNER_CHAT_ID to cfo_bot environment" && git push`
5. Дождаться деплоя на VPS через GitHub Actions (проверить что workflow прошёл зелёным)
6. После деплоя подключиться к VPS и проверить что scheduler стартовал: `ssh root@91.99.2.146 "cd /opt/cfo-brain && make logs | grep -i scheduler"`
7. Повторить проверки 1 и 7 из Task #4:
   - Проверка 1: Scheduler стартовал — должен показывать "Scheduler started" вместо "OWNER_CHAT_ID not set, scheduler disabled"
   - Проверка 7: Принудительный запуск weekly_digest — должен отправлять сообщение в Telegram
8. Обновить PROJECT_SNAPSHOT.md и DEV_LOG.md с результатами

## Definition of Done
- [ ] OWNER_CHAT_ID добавлен в environment сервиса cfo_bot в docker-compose.yml
- [ ] После git push и редеплоя: `make logs | grep -i scheduler` показывает "Scheduler started"
- [ ] Проверка 1 и 7 из Task #4 повторены и оба ✅ PASS
- [ ] PROJECT_SNAPSHOT.md обновлён с завершением Task #5
- [ ] DEV_LOG.md обновлён с записью о Task #5

## Observations outside scope
(Engineer заполняет в конце - наблюдения вне scope, не применённые)