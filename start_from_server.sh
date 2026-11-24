#!/bin/sh
# Start led_interface.py in the background, from the folder this script is in
# (/opt/led_strips on the Pi).
# Uses the venv in that folder if there is one (override with VENV=...).
cd "$(dirname "$0")" || exit 1

VENV="${VENV:-$PWD/venv}"
if [ -x "$VENV/bin/python" ]; then
    PYTHON="$VENV/bin/python"
else
    PYTHON=python3
fi

"$PYTHON" led_interface.py &
