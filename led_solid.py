#!/usr/bin/env python3
"""Hardware test: fade the whole strip through blue, green and red.

Uses the Arduino's "one colour for every LED" command (0x01, r, g, b).
Stop led_interface.py first, since only one program can use the serial port.
"""

import time

import serial

ser = serial.Serial('/dev/ttyACM0', 500000, write_timeout=0, timeout=5)
print(ser.readline().decode('ascii', errors='replace').strip())
time.sleep(1)
print('GO! (Ctrl+C to stop)')

i = 0
try:
    while True:
        level = i % 255
        for color in ((0, 0, level), (0, level, 0), (level, 0, 0)):
            ser.write(bytes([1, *color]))
            time.sleep(0.016)
        i += 1
except KeyboardInterrupt:
    ser.write(bytes([1, 0, 0, 0]))
finally:
    ser.close()
