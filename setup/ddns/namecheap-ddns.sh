#!/bin/sh
# Point a Namecheap dynamic DNS record at this network's public IPv4 address.
# Run every 10 minutes by namecheap-ddns.timer. Settings (host, domain, the
# Dynamic DNS password) are in /etc/namecheap-ddns.conf, which only root can read;
# systemd hands it to this script without it ever being readable by the service user.
set -eu

conf="${CREDENTIALS_DIRECTORY:+$CREDENTIALS_DIRECTORY/ddns.conf}"
conf="${conf:-/etc/namecheap-ddns.conf}"
DDNS_HOST= DDNS_DOMAIN= DDNS_PASSWORD=
. "$conf"
if [ -z "$DDNS_HOST" ] || [ -z "$DDNS_DOMAIN" ] || [ -z "$DDNS_PASSWORD" ]; then
    echo "Fill in DDNS_HOST, DDNS_DOMAIN and DDNS_PASSWORD in /etc/namecheap-ddns.conf" >&2
    exit 1
fi

# Leaving out the ip parameter makes Namecheap use the address the request comes
# from, i.e. the router's public IPv4 address (-4: never over IPv6). The URL goes
# to curl on stdin, so the password doesn't show up in the process list.
reply=$(printf 'url = "https://dynamicdns.park-your-domain.com/update?host=%s&domain=%s&password=%s"\n' \
            "$DDNS_HOST" "$DDNS_DOMAIN" "$DDNS_PASSWORD" |
        curl -4 -fsS --max-time 30 --config -)

if printf '%s' "$reply" | grep -q '<ErrCount>0</ErrCount>'; then
    ip=$(printf '%s' "$reply" | sed -n 's:.*<IP>\([^<]*\)</IP>.*:\1:p')
    echo "$DDNS_HOST.$DDNS_DOMAIN -> $ip"
else
    err=$(printf '%s' "$reply" | sed -n 's:.*<Err1>\([^<]*\)</Err1>.*:\1:p')
    echo "Namecheap refused the update: ${err:-unexpected reply}" >&2
    exit 1
fi
