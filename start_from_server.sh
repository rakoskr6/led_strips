#!/bin/sh
# Start led_interface.py in the background.
# Uses the venv in /home/pi/led_strips/venv if there is one (override with VENV=...).
cd /home/pi/led_strips || exit 1

VENV="${VENV:-/home/pi/led_strips/venv}"
if [ -x "$VENV/bin/python" ]; then
    PYTHON="$VENV/bin/python"
else
    PYTHON=python3
fi

"$PYTHON" led_interface.py &
