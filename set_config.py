#!/usr/bin/env python3
"""Change one setting in config.json. Used by the website.

    set_config.py <key> <value>

The value is converted to the type the setting already has in config.json
(true/false, whole number, decimal or text). Unknown keys are ignored with a
warning, and an invalid value leaves the file unchanged.
"""

import json
import os
import sys
import tempfile

CONFIG_FILE = '/home/pi/led_strips/config.json'


def convert(value, original_value):
    if isinstance(original_value, bool):
        lowered = value.strip().lower()
        if lowered not in ('true', 'false'):
            raise ValueError('expected true or false, got ' + repr(value))
        return lowered == 'true'
    if isinstance(original_value, int):
        number = float(value)
        # Keep whole numbers whole, but don't silently round "0.5" to 0.
        return int(number) if number.is_integer() else number
    if isinstance(original_value, float):
        return float(value)
    return str(value)


def write_config(path, text):
    """Replace the file in one step so led_interface.py never reads half a file."""
    directory = os.path.dirname(os.path.abspath(path))
    try:
        fd, temp_path = tempfile.mkstemp(prefix='.config.', suffix='.tmp', dir=directory)
    except OSError:
        # The website's user may only be allowed to write the file itself, not
        # create files next to it; fall back to writing it in place.
        with open(path, 'w') as fp:
            fp.write(text)
        return
    try:
        with os.fdopen(fd, 'w') as fp:
            fp.write(text)
        try:
            os.chmod(temp_path, os.stat(path).st_mode & 0o7777)
        except OSError:
            os.chmod(temp_path, 0o644)
        os.replace(temp_path, path)
    except BaseException:
        os.unlink(temp_path)
        raise


def set_config(key, value):
    print("Setting value in config " + str((key, value)))
    with open(CONFIG_FILE, 'r') as fp:
        data = json.load(fp)

    if key in data:
        try:
            data[key] = convert(value, data[key])
        except ValueError as e:
            sys.exit("Invalid value for {}: {}".format(key, e))
    else:
        print("Warning: unknown key {!r}, config not changed".format(key), file=sys.stderr)

    print("Writing config")
    text = json.dumps(data, indent=4)
    print(text)
    write_config(CONFIG_FILE, text)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise Exception("Only 2 arguments are allowed (key & value)")
    set_config(sys.argv[1], sys.argv[2])
