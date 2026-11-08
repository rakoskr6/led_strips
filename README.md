# led_strips
Lights that will dance to the music for Christmas!

A Raspberry Pi listens to music through an Audio Injector sound card, turns the
loudness of the bass into brightness, and streams colours over USB to an
Arduino Mega that drives 500 WS2812B LEDs. Pixelblaze controllers on the
network can follow along.

## Files

| File | What it is |
| --- | --- |
| `led_interface.py` | The main program |
| `config.json` | Settings, re-read every frame. Change them with `set_config.py <key> <value>` |
| `colorsettings.txt` | The two custom colours (first two lines, `r,g,b` from 0 to 1) |
| `network.cfg` | Pixelblaze addresses (not in git, see below) |
| `status.log` | Written every second with the PID and time, so the website can tell it's running |
| `map.py` | Where each LED sits on the tree, used for image mode |
| `images/` | Pictures and GIFs for image mode |
| `arduino_code/` | FastLED firmware for the Arduino Mega |
| `pixelblaze.js` | Pattern that runs on the Pixelblazes |
| `led_solid.py` | Hardware test that fades the whole strip |
| `website_*_volume.sh` | Get and set the input volume (used by the website) |

## Setup (Raspberry Pi OS, Python 3)

Install the Python packages from apt and create a venv that can see them:

```sh
sudo apt install python3-numpy python3-scipy python3-pil python3-serial python3-websocket python3-pyaudio
python3 -m venv --system-site-packages /home/pi/led_strips/venv
```

Audio Injector drivers: https://github.com/Audio-Injector/stereo-and-zero

```sh
sudo dpkg -i audio.injector.scripts_0.1-1_all.deb
```

`network.cfg` looks like this (one section per Pixelblaze):

```ini
[pixelblaze]
enabled = true
address = 192.168.1.50:81

[pixelblaze_cabinets]
enabled = false
address = 192.168.1.51:81
```

Run it from this folder (systemd runs it with
`WorkingDirectory=/home/pi/led_strips`):

```sh
cd /home/pi/led_strips
venv/bin/python led_interface.py
```
