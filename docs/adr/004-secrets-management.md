# ADR-004: Secrets management — Local .env + /opt/secrets/ distribution

## Статус
Accepted

## Контекст
Проект управляет секретами: RESTIC_PASSWORD, S3_ACCESS_KEY, S3_SECRET_KEY,
S3_BUCKET, S3_ENDPOINT, YANDEX_DISK_TOKEN, а также app-layer секретами
(BIFROST_* и другими). Внешние менеджеры секретов создают SPOF и усложняют
развёртывание.

Требования:
- Убрать внешние зависимости при развертывании
- Единственный источник правды — локальный `.env` в корне репозитория
- App-слой (Repo 1) ожидает секреты в `/opt/secrets/<app>.env`
- Безопасное хранение: chmod 600, root:root

## Решение
Однослойная система с локальным `.env` и автоматической дистрибуцией:

1. `deploy/secrets.py template` — создаёт `.env` с шаблоном (chmod 600), если его нет
2. `deploy/secrets.py validate` — проверяет наличие обязательных ключей (RESTIC_PASSWORD)
3. `deploy/secrets.py sync` — читает `.env`, валидирует, генерирует `/opt/secrets/<app>.env`

**Формат ключей:** стандартный ENV без слэшей (`RESTIC_PASSWORD`, `S3_ACCESS_KEY`).

**Дистрибуция:** переменные с префиксом `BIFROST_` → `/opt/secrets/bifrost.env`
с отрезанным префиксом (`BIFROST_OPENAI_KEY` → `OPENAI_KEY`).

Поток:
```
.env (root:root 600) → secrets.py sync → /opt/secrets/bifrost.env (root:root 600)
                                           /opt/secrets/<app>.env
                                                    ↓
                                            App-слой (Repo 1)
```

## Альтернативы
- **Bitwarden Secrets Manager**: SPOF, требует токена и доступа к API
- **Hashicorp Vault**: overkill для single-VPS, сложный bootstrap
- **Mozilla SOPS**: требует GPG/KMS, нет потоковой дистрибуции
- **Ansible Vault**: зависит от Ansible, проект без Ansible

## Последствия
- Нет внешних зависимостей — deploy работает без интернета (кроме apt)
- `.env` — root:root chmod 600, никогда не попадает в репозиторий (.gitignore)
- `/opt/secrets/` — root:root chmod 700, файлы chmod 600
- Restic настроен на бэкап `/opt/secrets/`
- При отсутствии `.env` deploy.sh падает с понятной ошибкой
- Secrets.py — 3 команды: sync, validate, template
