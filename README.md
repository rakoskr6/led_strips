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
| `setup/` | Everything else the Pi needs: firewall, SSH, sound card, the systemd service, the website's Apache config, dynamic DNS. See [setup/README.md](setup/README.md) |

## Setup (Raspberry Pi OS, Python 3)

This is the short version. [MIGRATION.md](MIGRATION.md) has the full, checked
list from the last rebuild, and [setup/README.md](setup/README.md) explains each
piece and the everyday commands.

The code lives in `/opt/led_strips`, so it doesn't depend on the login name and
the website can reach it:

```sh
sudo apt install git
sudo mkdir -p /opt/led_strips && sudo chown "$USER": /opt/led_strips
git clone https://github.com/rakoskr6/led_strips /opt/led_strips
```

Install the Python packages from apt and create a venv that can see them:

```sh
sudo apt install python3-venv python3-numpy python3-scipy python3-pil python3-serial python3-websocket python3-pyaudio
python3 -m venv --system-site-packages /opt/led_strips/venv
```

Sound card: the Audio Injector's overlay ships with Raspberry Pi OS, so the old
`.deb` isn't needed. Add `dtoverlay=audioinjector-wm8731-audio` (and
`dtparam=audio=off`) to `/boot/firmware/config.txt`, then load the mixer
settings from [setup/alsa/](setup/alsa/) (see setup/README.md).

`network.cfg` looks like this (one section per Pixelblaze):

```ini
[pixelblaze]
enabled = true
address = 192.168.1.50:81

[pixelblaze_cabinets]
enabled = false
address = 192.168.1.51:81
```

systemd runs it at boot as `led-strips.service`
([setup/led-strips.service](setup/led-strips.service)):

```sh
systemctl status led-strips          # is it running?
journalctl -u led-strips -f          # its log
```

To run it by hand, stop the service first (only one program can use the Arduino):

```sh
sudo systemctl stop led-strips
cd /opt/led_strips && venv/bin/python led_interface.py
```

## Tests

The tests use a fake Arduino, fake audio and fake Pixelblazes, so they don't
need the hardware and are safe to run while the lights are on:

```sh
cd /opt/led_strips
venv/bin/python -m unittest discover -s tests -v
```
