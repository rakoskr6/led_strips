#!/bin/bash
# Step 5 of MIGRATION.md: Apache + PHP for the lights' website, and the website's
# (limited) access to the lights. Safe to run again.
#   sudo bash /opt/led_strips/setup/install-website.sh
# Expects the site checked out at /var/www/christmas_led_site (owned by krakos).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
LED=/opt/led_strips
SITE=/var/www/christmas_led_site
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo." >&2; exit 1; }
[ -f "$SITE/index.php" ] || { echo "Clone christmas_led_site to $SITE first." >&2; exit 1; }

echo "== 1/4 Packages =="
apt-get -y install apache2 libapache2-mod-php

echo "== 2/4 Apache and PHP config =="
install -m 644 "$HERE/apache/led-site.conf" /etc/apache2/sites-available/led-site.conf
install -m 644 "$HERE/apache/zz-led-site.conf" /etc/apache2/conf-available/zz-led-site.conf
php_dir=$(ls -d /etc/php/*/apache2 | sort -V | tail -1)
install -m 644 "$HERE/apache/php-led-site.ini" "$php_dir/conf.d/99-led-site.ini"
a2dissite -q 000-default || true
a2ensite -q led-site
a2enconf -q zz-led-site
# Folder listings and the /server-status page aren't used
a2dismod -q -f autoindex status || true
apache2ctl configtest
systemctl reload apache2

echo "== 3/4 What the website (www-data) may do =="
# Read status.log and write config.json; everything else stays krakos's and read-only.
# setgid on the folder: files replaced there (status.log, config.json) keep group www-data.
chgrp www-data "$LED" "$LED/config.json"
chmod 2755 "$LED"
chmod 664 "$LED/config.json"
# Start/stop the lights service, nothing else
visudo -cf "$HERE/sudoers-led-strips"
install -m 440 "$HERE/sudoers-led-strips" /etc/sudoers.d/led-strips
# Set the capture volume with amixer
usermod -aG audio www-data
systemctl restart apache2    # so Apache's processes pick up the new group

echo "== 4/4 Check =="
id www-data
sudo -u www-data sudo -n -l | tail -2
sudo -u www-data test -r "$LED/status.log" && echo "www-data can read status.log"
sudo -u www-data test -w "$LED/config.json" && echo "www-data can write config.json"
sudo -u www-data test -w "$LED/led_interface.py" || echo "www-data can't change the code (good)"
echo "Website set up: http://$(hostname).local/"
