#!/bin/bash
# base-mais-server-setup — Server provisioning & CIS audit
# Usage:
#   sudo bash deploy/deploy.sh
#
# Or from SSH:
#   ssh user@host
#   sudo apt update && sudo apt install -y git
#   git clone <repo-url> .   # e.g. https://github.com/mlenkov/base-mais-server-setup.git
#   sudo bash deploy/deploy.sh

set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# === Server mode: must run as root ===
if [ "$EUID" -ne 0 ]; then
    exec sudo bash "$0" "$@"
fi

ORIGINAL_USER="${SUDO_USER:-$(who am i | awk "{print \$1}")}"
if [ -z "$ORIGINAL_USER" ] || [ "$ORIGINAL_USER" = "root" ]; then
    ORIGINAL_HOME="$HOME"
else
    ORIGINAL_HOME=$(eval echo "~$ORIGINAL_USER")
fi

PROJECT_DIR="$ORIGINAL_HOME"
DOCS_DIR="$ORIGINAL_HOME/docs"

# Detect origin URL (for forkers)
REPO_URL="${REPO_URL:-$(git remote get-url origin 2>/dev/null || echo 'https://github.com/mlenkov/base-mais-server-setup.git')}"

# Auto-relocate if cloned into subdirectory (git clone without .)
SUB_DIR="$PROJECT_DIR/base-mais-server-setup"
if [ -d "$SUB_DIR" ]; then
    echo "→ Обнаружена подпапка base-mais-server-setup, перемещаю содержимое..."
    shopt -s dotglob 2>/dev/null || true
    for f in "$SUB_DIR"/*; do
        [ -e "$f" ] && mv -f "$f" "$PROJECT_DIR/" 2>/dev/null || true
    done
    rmdir "$SUB_DIR" 2>/dev/null || true
    shopt -u dotglob 2>/dev/null || true
fi

echo "===== base-mais-server-setup — Server Provisioning ====="

# Clean dpkg locks from any previous interrupted install
rm -f /var/lib/dpkg/lock /var/lib/dpkg/lock-frontend \
      /var/cache/apt/archives/lock /var/lib/apt/lists/lock
dpkg --configure -a 2>/dev/null || true

# Install all deps upfront (avoids dpkg lock issues in cis_manager)
apt-get update -qq 2>/dev/null || true
apt-get install -y -qq \
  -o Dpkg::Options::="--force-confdef" \
  -o Dpkg::Options::="--force-confold" \
  git python3 python3-venv restic rclone curl \
  chrony needrestart unattended-upgrades nftables zram-tools

# === ZRAM: compressed swap in RAM (save SSD IOPS) ===
echo "⚡ Настройка ZRAM..."
cat > /etc/default/zram-tools << 'ZRAMEOF'
# ZRAM configuration for Free-Tier (cloud.ru): save SSD IOPS
ALGO=zstd
PERCENT=50
PRIORITY=100
ZRAMEOF

# Remove any existing disk-based swap (kills SSD IOPS)
swapoff -a 2>/dev/null || true
sed -i '/swap/d' /etc/fstab 2>/dev/null || true

systemctl enable --now zramswap 2>/dev/null || true

# Kernel params for ZRAM: aggressive page compression, keep VFS cache
cat > /etc/sysctl.d/99-zram.conf << 'SYSCTLEOF'
vm.swappiness=60
vm.vfs_cache_pressure=50
SYSCTLEOF
sysctl --system 2>/dev/null || true

# === Journald — жесткое ограничение логов (30 ГБ SSD Free-Tier) ===
mkdir -p /etc/systemd/journald.conf.d
cat > /etc/systemd/journald.conf.d/99-mais.conf << 'EOF'
[Journal]
SystemMaxUse=500M
SystemMaxFileSize=50M
MaxRetentionSec=7day
EOF
systemctl restart systemd-journald

cd "$PROJECT_DIR"
python3 -m venv /opt/provisioning-venv
source /opt/provisioning-venv/bin/activate
pip install --upgrade pip -q
pip install -q -r requirements.txt
PYTHON_BIN=/opt/provisioning-venv/bin/python3

$PYTHON_BIN deploy/secrets.py sync
set -a; source .env 2>/dev/null || true; set +a

$PYTHON_BIN cis/manager.py audit --format json
$PYTHON_BIN cis/manager.py fix --force

# nftables: default-deny firewall (SSH only)
cat > /etc/nftables.conf << 'EOF'
#!/usr/sbin/nft -f
flush ruleset
table inet filter {
  chain input { type filter hook input priority 0; policy drop;
    ct state established,related accept
    iif lo accept
    tcp dport 22 accept
    icmp type { echo-request, echo-reply } accept
  }
  chain forward { type filter hook forward priority 0; policy drop; }
  chain output { type filter hook output priority 0; policy accept; }
}
include "/etc/nftables.d/*.nft"
EOF
systemctl enable --now nftables 2>&1 || true
nft -f /etc/nftables.conf 2>&1 || true

# Docker bridge forward rules (чтобы не блокировать трафик контейнеров)
mkdir -p /etc/nftables.d
cat > /etc/nftables.d/99-docker-bridge.nft << 'NFTEOF'
#!/usr/sbin/nft -f
# Managed by base-mais-server-setup
add rule inet filter forward iifname "br-*" counter accept
add rule inet filter forward oifname "br-*" counter accept
add rule inet filter forward iifname "docker0" counter accept
add rule inet filter forward oifname "docker0" counter accept
NFTEOF
nft -f /etc/nftables.d/99-docker-bridge.nft 2>/dev/null || true

$PYTHON_BIN cis/manager.py audit --format json

# Don't exit on compliance fail — let backup + docs run
$PYTHON_BIN cis/check_compliance.py --threshold 95 || true

ionice -c 3 nice -n 19 $PYTHON_BIN backup/backup.py setup 2>/dev/null || true
ionice -c 3 nice -n 19 $PYTHON_BIN backup/backup.py create 2>/dev/null || true
$PYTHON_BIN deploy/docs_generator.py

mkdir -p "$DOCS_DIR"
cp docs/SERVER.md "$DOCS_DIR/" 2>/dev/null || true

# Cleanup deploy artifacts (one-shot, not needed on running server)
rm -rf "$PROJECT_DIR/deploy"
rm -rf "$PROJECT_DIR/.git" "$PROJECT_DIR/.github" "$PROJECT_DIR/requirements.txt"

# Удаление пакетов разработки (не нужны на production)
apt-get remove -y --purge --auto-remove \
  build-essential gcc g++ python3-dev \
  python3-wheel 2>/dev/null || true

# Мониторинг здоровья (диск, память, load)
(crontab -l 2>/dev/null || true
 echo "0 8 * * * cd $PROJECT_DIR && ionice -c 3 nice -n 19 $PYTHON_BIN backup/monitor.py >> /var/log/monitor.log 2>&1"
) | crontab -

chown -R "$ORIGINAL_USER:$ORIGINAL_USER" "$PROJECT_DIR"

echo "===== Done ====="
echo "Project: $PROJECT_DIR"
echo "Docs:    $DOCS_DIR/SERVER.md"
