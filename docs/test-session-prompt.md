# Prompt for next full deploy test

Скопируй и отправь новой сессии агента:

---

Начать настройку сервера с нуля. Репозиторий уже склонирован.

```
IP: 91.224.87.211
SSH user: mais
SSH key: ~/.ssh/MacBuka
```

Выполни шаги:

1. SSH на сервер (с `-o ServerAliveInterval=60`), перейти в `~` и сделать `git pull`
2. Запустить: `sudo bash deploy/deploy.sh`
3. Дождись полного завершения deploy.sh

После завершения составь отчёт со следующими секциями:

### Общая информация
- IP, hostname, версия ОС

### Secrets
- Валидирован ли .env
- Созданы ли файлы в /opt/secrets/

### CIS Audit
- Результаты до fix (PASS/FAIL/Error)
- Результаты после fix
- Compliance %
- Сколько проверок всего

### Backup
- Локальный: статус
- S3: статус (должен работать)
- Yandex Disk: статус
- Cron: настроен/нет

### Ошибки и баги
- Какие ошибки встретились в процессе
- Любые неожиданные ⏭️ или ❌

### AIDE
- Статус инициализации БД (`aide.db` должна быть активирована, не `aide.db.new`)
- Время инициализации

### Что должно работать (все фиксы применены)
- CIS 59/59 (100%)
- Backup: S3 + Yandex Disk (две копии, без локальной)
- AIDE: автоматическая активация БД (poll до 5 мин)
- `backup.py status`: работает от любого пользователя (cron через sudo)
- SSH: не обрывается по таймауту (ServerAliveInterval=60)

## Ускоренное тестирование
Для полного цикла без переустановки ОС:
```bash
ssh -o ServerAliveInterval=60 -i ~/.ssh/MacBuka mais@91.224.87.211
cd ~ && git pull
sudo python3 deploy/tests/test_deploy.py
```
Скрипт сделает снепшот → deploy → CIS fix loop → audit → rollback → verify → re-deploy → отчёт.

Цикл fix (до 5 итераций): audit → если < 100% → fix → audit → repeat. Число итераций и результат каждой — в отчёте.
