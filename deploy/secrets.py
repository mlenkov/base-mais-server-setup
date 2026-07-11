#!/usr/bin/env python3
"""
Local Secret Manager — .env validation + distribution to /opt/secrets/
"""

import argparse
import os
import sys
from pathlib import Path

REQUIRED_KEYS = ["RESTIC_PASSWORD"]
SECRETS_DIR = Path("/opt/secrets")

TEMPLATE = """# === REQUIRED (backup не будет работать без этого) ===
RESTIC_PASSWORD=''

# === cloud.ru S3 (опционально) ===
S3_ACCESS_KEY=''
S3_SECRET_KEY=''
S3_BUCKET=''
S3_ENDPOINT=''
S3_TENANT_ID=''

# === Yandex Disk (опционально) ===
YANDEX_DISK_TOKEN=''

# === App-layer secrets (опционально) ===
# Префикс будет отрезан при генерации /opt/secrets/<app>.env
# Пример: BIFROST_OPENAI_KEY → OPENAI_KEY в /opt/secrets/bifrost.env
# BIFROST_OPENAI_KEY=''
# BIFROST_ANTHROPIC_KEY=''
"""


def _parse_env(text: str) -> dict:
    env = {}
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("'\"")
    return env


def _validate(env: dict):
    missing = [k for k in REQUIRED_KEYS if not env.get(k)]
    if missing:
        print(f"❌ Отсутствуют обязательные ключи: {', '.join(missing)}")
        print("   Заполните .env и запустите deploy.sh повторно")
        sys.exit(1)


def _write_app_envs(env: dict):
    """Generate /opt/secrets/<app>.env for prefixed variables."""
    app_envs = {}
    for key, value in env.items():
        if "_" in key:
            prefix, _, rest = key.partition("_")
            if rest and prefix.isupper() and prefix not in (
                "RESTIC", "S3", "YANDEX", "AWS"
            ):
                app_envs.setdefault(prefix.lower(), {})[rest] = value

    if not app_envs:
        return

    SECRETS_DIR.mkdir(parents=True, exist_ok=True)

    for app_name, vars in app_envs.items():
        app_file = SECRETS_DIR / f"{app_name}.env"
        content = "".join(
            f"{k}='{v.replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'\n"
            for k, v in sorted(vars.items())
        )
        app_file.write_text(content, encoding="utf-8")
        app_file.chmod(0o600)
        os.chown(app_file, 0, 0)
        print(f"  📄 Создан {app_file} ({len(vars)} ключей)")

    os.chown(SECRETS_DIR, 0, 0)
    SECRETS_DIR.chmod(0o700)


def cmd_sync(args):
    env_path = Path(args.env)

    if not env_path.exists():
        env_path.write_text(TEMPLATE, encoding="utf-8")
        env_path.chmod(0o600)
        print(f"📄 Создан шаблон {env_path} (chmod 600)")
        print("⚠️  Заполните .env файл и запустите deploy.sh повторно")
        sys.exit(1)

    env = _parse_env(env_path.read_text(encoding="utf-8"))
    _validate(env)
    _write_app_envs(env)

    if SECRETS_DIR.exists():
        print(f"✅ Секреты распределены в {SECRETS_DIR}/")
    print(f"✅ .env валиден ({len(env)} ключей)")


def cmd_validate(args):
    env_path = Path(args.env)
    if not env_path.exists():
        print(f"❌ {env_path} не найден")
        sys.exit(1)

    env = _parse_env(env_path.read_text(encoding="utf-8"))
    _validate(env)
    print(f"✅ .env валиден ({len(env)} ключей)")


def cmd_template(args):
    env_path = Path(args.env)
    if env_path.exists():
        print(f"⚠️  {env_path} уже существует, пропускаю")
        return
    env_path.write_text(TEMPLATE, encoding="utf-8")
    env_path.chmod(0o600)
    print(f"📄 Создан шаблон {env_path} (chmod 600)")
    print("⚠️  Заполните .env файл и запустите deploy.sh повторно")


def main():
    parser = argparse.ArgumentParser(
        description="Local Secret Manager — .env validation + distribution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  %(prog)s sync                      # Валидация .env + распределение в /opt/secrets/
  %(prog)s validate                  # Только валидация .env
  %(prog)s template                  # Создать шаблон .env

Переменные окружения (в .env):
  RESTIC_PASSWORD    - Пароль шифрования restic (обязательно)
  S3_ACCESS_KEY      - S3 Access Key
  S3_SECRET_KEY      - S3 Secret Key
  S3_BUCKET          - Имя S3 бакета
  S3_ENDPOINT        - S3 endpoint URL
  S3_TENANT_ID       - S3 Tenant ID
  YANDEX_DISK_TOKEN  - Yandex Disk OAuth token
  BIFROST_*          - App-layer секреты (→ /opt/secrets/bifrost.env)
        """,
    )

    parser.add_argument("--env", default=".env", help="Путь к .env файлу (по умолч. .env)")

    subparsers = parser.add_subparsers(dest="command", help="Команды")
    subparsers.add_parser("sync", help="Валидация .env + распределение в /opt/secrets/")
    subparsers.add_parser("validate", help="Только валидация .env")
    subparsers.add_parser("template", help="Создать шаблон .env")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "sync":
        cmd_sync(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "template":
        cmd_template(args)


if __name__ == "__main__":
    main()
