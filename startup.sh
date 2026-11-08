#!/bin/sh
# Starts the lights by hand or from cron (@reboot /home/pi/led_strips/startup.sh).
# On the current Pi, systemd starts led_interface.py instead, and the mixer
# settings are restored at boot by alsactl, so this script is optional.
#
# Set USE_JACK=1 to start the JACK audio server first.

if [ "${USE_JACK:-0}" = "1" ]; then
    jack_control start || echo "startup.sh: could not start JACK, continuing without it" >&2
fi

exec sh /home/pi/led_strips/start_from_server.sh
