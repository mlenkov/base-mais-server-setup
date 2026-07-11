# ADR-003: Immutable Infrastructure — AIDE не используется

## Статус
Superseded — AIDE и auditd удалены из provisioning.

## Контекст
Ранее AIDE использовался для мониторинга целостности файловой системы (SHA-512 хеши).
На Free-Tier (cloud.ru, 30 ГБ SSD, 2 vCPU @ 10%) AIDE и auditd генерируют избыточную
I/O нагрузку, вызывая таймауты Docker healthcheck-ов App-слоя.

## Решение
**Immutable Infrastructure** — если сервер скомпрометирован, он пересоздаётся.
- AIDE не устанавливается и не инициализируется
- auditd не устанавливается
- Экономия: ~500 MB I/O в день + 2% CPU

Безопасность обеспечивается:
- Key-only SSH (пароль отключён)
- nftables default-deny (только SSH)
- Регулярные CIS аудиты (59 проверок)
- Ежедневный 1-2-1 backup для быстрого восстановления

## Альтернативы
- **AIDE + ionice**: всё равно генерирует I/O при сканировании inode
- **auditd с фильтрацией**: сложная конфигурация, не отменяет логирование в журнал
- **Osquery/Falco**: overkill для single-VPS Free-Tier

## Последствия
- `deploy.sh` не устанавливает aide, auditd
- `cis/standard.yaml` не содержит checks для aide/auditd
- При компрометации — пересоздание VPS + restore из backup
