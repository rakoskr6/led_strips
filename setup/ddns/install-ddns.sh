#!/bin/bash
# Installs the Namecheap dynamic DNS timer. Safe to run again.
#   sudo bash /opt/led_strips/setup/ddns/install-ddns.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo." >&2; exit 1; }

conf=/etc/namecheap-ddns.conf
if [ ! -f "$conf" ]; then
    install -m 600 -o root -g root "$HERE/namecheap-ddns.conf.example" "$conf"
fi
chmod 600 "$conf"; chown root:root "$conf"

install -m 644 "$HERE/namecheap-ddns.service" "$HERE/namecheap-ddns.timer" /etc/systemd/system/
systemctl daemon-reload

if grep -q '^DDNS_PASSWORD=.\+' "$conf" && ! grep -q '^DDNS_DOMAIN=example.com' "$conf"; then
    systemctl start namecheap-ddns.service      # update now, and show the result
    journalctl -u namecheap-ddns -n 3 --no-pager -o cat
    systemctl enable --now namecheap-ddns.timer
    systemctl list-timers namecheap-ddns.timer --no-pager
else
    echo "Now edit $conf (sudo nano $conf): set the domain and the Dynamic DNS password,"
    echo "then run this script again."
fi
