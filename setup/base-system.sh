#!/bin/bash
# Step 1 of MIGRATION.md: base system hardening for the LED Pi.
# Run it from your own SSH terminal (it asks you to confirm the firewall):
#   sudo bash /opt/led_strips/setup/base-system.sh
# You can run it again safely.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo." >&2; exit 1; }

echo "== 1/4 Packages =="
apt-get update
apt-get -y full-upgrade
apt-get -y install unattended-upgrades
# Turn on the daily apt update and unattended upgrade (Debian security updates by default)
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF

echo "== 2/4 SSH: keys only =="
conf=/etc/ssh/sshd_config.d/10-local.conf
[ -f "$conf" ] && cp -p "$conf" "$conf.prev"
install -m 644 "$HERE/sshd-10-local.conf" "$conf"
# A broken sshd config would stop SSH starting at the next boot, so put the old one back
if ! sshd -t; then
    if [ -f "$conf.prev" ]; then mv "$conf.prev" "$conf"; else rm -f "$conf"; fi
    echo "New SSH config is invalid; kept the old one." >&2
    exit 1
fi
rm -f "$conf.prev"
systemctl reload ssh
sshd -T | grep -E '^(passwordauthentication|kbdinteractiveauthentication|permitrootlogin|x11forwarding|pubkeyauthentication|allowusers|maxauthtries|logingracetime|persourcepenalties) '

echo "== 3/4 Firewall =="
nft -c -f "$HERE/nftables.conf"            # syntax check only
backup="$(mktemp /root/nft-before.XXXXXX)"
nft list ruleset > "$backup"

rollback() {
    nft flush ruleset
    nft -f "$backup"
    echo "Firewall rolled back to the previous rules. Nothing was saved." >&2
}

# If this SSH session drops, keep running so the rollback still happens.
trap '' HUP
nft -f "$HERE/nftables.conf"
echo
echo "Firewall is now active, but not saved."
echo "From your PC, open a NEW ssh session to this Pi to check you can still get in."
echo "Then type 'yes' here within 120 seconds, or the rules are rolled back."
if read -r -t 120 answer && [ "$answer" = yes ]; then
    install -m 755 "$HERE/nftables.conf" /etc/nftables.conf
    systemctl enable nftables.service
    echo "Saved to /etc/nftables.conf; it loads at every boot."
else
    rollback
    exit 1
fi
trap - HUP

echo "== 4/4 Check =="
id krakos
systemctl is-enabled nftables unattended-upgrades.service apt-daily-upgrade.timer
echo "Step 1 done."
