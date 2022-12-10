#!/usr/bin/env python

import json
import sys

CONFIG_FILE='/home/pi/led_lights/config.json'

def set_config(key, value):
    print("Setting value in config " + (key, value))
    with open(CONFIG_FILE, 'rw') as fp:
        data = json.load(fp)
        if key in data:
            data[key] = value

        fp.seek(0)
        fp.write(json.dumps(data, indent=4))
        fp.truncate()

if len(sys.argv) != 3:
    raise Exception("Only 2 arguments are allowed (key & value)")

set_config(sys.argv[1], sys.argv[2])