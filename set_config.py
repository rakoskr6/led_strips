#!/usr/bin/env python

import json
import sys

CONFIG_FILE='/home/pi/led_strips/config.json'

def set_config(key, value):
    print("Setting value in config " + str((key, value)))
    data = {}
    with open(CONFIG_FILE, 'r') as fp:
        data = json.load(fp)
        if key in data:
            original_value = data.get(key)
            if type(original_value) == bool:
                casted = value.lower() == "true"
            elif type(original_value) == float:
                casted = float(value)
            else:
                casted = str(value)
            data[key] = casted

    with open(CONFIG_FILE, 'w') as fp:
        print("Writing config")
        print(json.dumps(data, indent=4))
        fp.write(json.dumps(data, indent=4))

if len(sys.argv) != 3:
    raise Exception("Only 2 arguments are allowed (key & value)")

set_config(sys.argv[1], sys.argv[2])
