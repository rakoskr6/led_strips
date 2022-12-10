#!/usr/bin/env python

import json
import sys

CONFIG_FILE='/home/pi/led_strips/config.json'

def set_config(key, value):
    print("Setting value in config " + str((key, value)))
    with open(CONFIG_FILE, 'r') as fp:
        data = json.load(fp)
        if key in data:
            if typ == bool
            typ = type(key)
            data[key] = typ(value)

    with open(CONFIG_FILE, 'w') as fp:
        fp.truncate()
        fp.write(json.dumps(data, indent=4))

if len(sys.argv) != 3:
    raise Exception("Only 2 arguments are allowed (key & value)")

set_config(sys.argv[1], sys.argv[2])
