# Migration: Raspbian 9 (Stretch) → Raspberry Pi OS 13 (Trixie)

Hand-off notes for moving the LED lights and their control website from the old
SD card to a fresh Trixie install on the same Raspberry Pi 3 Model B. Based on a
review of a file-level backup of the old card plus the `python3-conversion`
branch. Items marked **unverified** need checking on the Pi.

This repo is public, so local IPs, Wi-Fi details, key names and other private
details are deliberately left out. They live in `network.cfg` and on the old card.

## Old system at a glance

| Piece | How it worked on Stretch |
|---|---|
| OS | Raspbian 9, desktop install with autologin, user `pi` |
| LED driver | `led_interface.py` run by Python 2 |
| LEDs | Arduino Mega running FastLED, USB serial `/dev/ttyACM0` at 500000 baud ([arduino_code/](arduino_code/)) |
| Wireless strips | Two Pixelblazes over websocket, addresses in `network.cfg` |
| Audio | Audio Injector stereo card, `dtoverlay=audioinjector-wm8731-audio`, onboard audio off, `~/.asoundrc` points ALSA default at `hw` card 0 |
| Mixer | `alsactl --file /usr/share/doc/audioInjector/asound.state.RCA.thru.test restore` at boot |
| JACK | Started at boot, but its log stops in Dec 2022 while the lights kept running, so it is probably unused (**unverified**) |
| Startup | `@reboot` crontab → `startup.sh` → `start_from_server.sh` |
| Website | Apache 2.4 + PHP 7.0, port 80 only, no HTTPS, no login, `APACHE_RUN_USER=pi`; web root `/var/www/html` |
| Site ↔ lights | PHP shells out to `set_config.py` (edits `config.json`), `website_get_volume.sh` / `website_set_volume.sh` (`amixer 'Capture'`), and `kill` / `start_from_server.sh` for start/stop; `status.php` reads `/home/pi/led_strips/status.log` |
| Exposure | Apache logs only ever showed LAN clients; no port forward, tunnel or VPN |

## Already done on `python3-conversion`

- [x] `led_interface.py` rewritten for Python 3 / NumPy 2: `numpy.frombuffer`, `time.time()`,
      no `colour` library, `#!/usr/bin/env python3`
- [x] Hue support removed (`phue`, [phue_leds.py], [phue_sbox.py] gone)
- [x] Image mode builds full 500-LED frames; silence no longer crashes or restarts the stream;
      each Pixelblaze sends from its own thread
- [x] Serial frames paced (`SHOW_GAP`) and the Arduino resynced at startup, for the
      "first LEDs show the wrong colour" bug; port opened `exclusive=True`, so a second copy exits
- [x] `status.log` written at most once a second, atomically (it was every frame)
- [x] `SIGTERM` handled, so `systemctl stop` closes the audio stream and serial port cleanly
- [x] [set_config.py](set_config.py) keeps numbers as numbers, rejects bad values and `inf`/`nan`,
      writes `config.json` atomically
- [x] [startup.sh](startup.sh) / [start_from_server.sh](start_from_server.sh): real shebangs, use
      `venv/` if present, JACK only with `USE_JACK=1`, no mixer restore (left to `alsactl` at boot)
- [x] [requirements.in](requirements.in) lists the real dependencies, all from apt; Python 2
      pip freeze, `graveyard/` and `temp.dat` deleted
- [x] [.gitattributes](.gitattributes) keeps text files LF, so a Windows checkout no longer breaks the scripts
- [x] 34 hardware-free tests in [tests/](tests/)

[phue_leds.py]: https://github.com/rakoskr6/led_strips/blob/master/phue_leds.py
[phue_sbox.py]: https://github.com/rakoskr6/led_strips/blob/master/phue_sbox.py

The code mentions a systemd service ([startup.sh:3](startup.sh:3), [led_interface.py:658](led_interface.py:658)),
but **no unit file is in the repo**. If one already exists on the new Pi, commit a copy
(see step 4).

## Decisions

- Fresh Trixie **Lite** install, user `pi` (paths hardcode `/home/pi`), Ethernet only.
- Python 3 from apt plus a `--system-site-packages` venv at `/home/pi/led_strips/venv`;
  nothing pip-installed. No Python 2, PyPy, PulseAudio or desktop; JACK only if the old
  system really used it.
- systemd runs the lights (`led-strips.service`), not cron or PHP.
- Apache runs as `www-data`, not `pi`.
- The site **will be reachable from the internet**, so it gets HTTPS, a login and
  POST-only actions before it is exposed. Preferred: a Cloudflare Tunnel (no router
  ports opened). Fallback: forward only 80/443 with dynamic DNS and Certbot.

## Where everything is

**In git**
- This repo: clone it on the Pi and check out `python3-conversion` (merge to `master`
  once it runs on the hardware). The old Pi's copy matched `master` apart from `config.json`.
- Website: [christmas_led_site](https://github.com/rakoskr6/christmas_led_site).
  **The GitHub copy is stale** (3 commits, Dec 2020). The live site on the old Pi
  is much newer and was never committed. The Pi's web root had been re-initialised
  with no commits. Missing from GitHub: `status.php`, `smallfooter.php`, `start/`,
  `options/`, `lights_all/`, `lights_pattern/`, `lights_tree/`,
  `assets/css/theme.min.css`, `assets/dark-bootstrap/`, and newer `index.php`,
  `header.php`, `footer.php`, `music/`, `patterns/`, `custom.css`,
  `landing-page.css`. **First job:** commit the old Pi's web root on top of the
  GitHub history and push it.

**Not in git, copy from the old card/backup**
- `~/led_strips/network.cfg` (Pixelblaze addresses; gitignored; format in [README.md](README.md))
- `~/led_strips/config.json` (live settings; differs from git)
- `/usr/share/doc/audioInjector/asound.state.RCA.thru.test` (the mixer state restored at boot)
- `/var/lib/alsa/asound.state` (last saved mixer state, card id `audioinjectorpi`)
- Two old stashes in the Pi's `led_strips` clone (`stash@{0}`, `stash@{1}`): review or drop
- Arduino tooling, only needed to reflash: `~/Arduino-Makefile`, `~/Downloads/FastLED`,
  `~/led_mapper/arduino_code` (`LightMapper.ino`)

**Root-only, missing from the Windows backup: recover from the old card**

Windows can't read ext4. Mount the old card read-only on the new Pi with a USB reader:

```bash
lsblk
sudo mkdir -p /mnt/oldsd && sudo mount -o ro /dev/sda2 /mnt/oldsd
mkdir -m 700 -p ~/old-sd && sudo cp -a /mnt/oldsd/var/spool/cron/crontabs /mnt/oldsd/etc/sudoers /mnt/oldsd/etc/sudoers.d /mnt/oldsd/root ~/old-sd/ && sudo chown -R "$USER": ~/old-sd
sudo umount /mnt/oldsd
```

To see what was actually *running* (JACK? which Python?), boot the old card
briefly on the LAN and run:

```bash
crontab -l; sudo crontab -l; ls -l /usr/bin/python; ps aux | grep -E 'led_interface|jack' | grep -v grep; cat /proc/asound/cards; amixer scontrols
```

**Do not carry over:** old SSH `authorized_keys` wholesale (keep only keys still
wanted), saved Wi-Fi networks, the old SSH private keys (make a new one and add it
to GitHub), anything from `/usr/local` (hand-built PortAudio, pip packages).

## Checklist

### 1. Base system
- [ ] `sudo apt update && sudo apt full-upgrade`, then `sudo apt install unattended-upgrades`
- [ ] Reserve the Pi's IP on the router (DHCP reservation)
- [ ] SSH keys only: `PasswordAuthentication no` in `/etc/ssh/sshd_config.d/`
- [ ] Firewall (nftables or ufw): SSH and HTTP from the LAN only
- [ ] `pi` in `dialout` and `audio` groups
- [ ] New SSH key for GitHub; clone this repo to `/home/pi/led_strips`, check out `python3-conversion`

### 2. Audio (riskiest part)
- [ ] `/boot/firmware/config.txt`: add `dtoverlay=audioinjector-wm8731-audio`;
      set `dtparam=audio=off`; use `dtoverlay=vc4-kms-v3d,noaudio` so HDMI audio
      doesn't take a card slot; add `dtoverlay=disable-wifi` (Ethernet only).
      Drop the old `pi3-disable-bt` / `enable_uart=0`; the Arduino is on USB, not the UART.
- [ ] Check the overlay exists: `ls /boot/firmware/overlays/audioinjector*` (**unverified** on Trixie)
- [ ] The Audio Injector `.deb` in [README.md](README.md) is from 2017 and may not install on Trixie
      (**unverified**). Its saved state file is enough without it.
- [ ] `aplay -l` / `arecord -l` show the card; confirm its id (`audioinjectorpi` on the old system)
- [ ] `~/.asoundrc`: reference the card **by name**, not `card 0`:
      ```
      pcm.!default { type hw card audioinjectorpi }
      ctl.!default { type hw card audioinjectorpi }
      ```
- [ ] Mixer: `sudo alsactl --file <saved RCA state> restore`, then `sudo alsactl store`.
      The branch's scripts rely on alsa-utils restoring the stored state at boot,
      so check it survives a reboot.
- [ ] `amixer sget 'Capture'` still works; [website_get_volume.sh](website_get_volume.sh) parses its output
- [ ] Line-in capture works at 32 kHz, 2 channels, full duplex
      (`AUDIO_RATE` / `AUDIO_CHANNELS`, [led_interface.py:60](led_interface.py:60))
- [ ] Install JACK only if the old system really used it

### 3. LED code on the hardware
```bash
sudo apt install python3-venv python3-numpy python3-scipy python3-pil python3-serial python3-websocket python3-pyaudio
python3 -m venv --system-site-packages /home/pi/led_strips/venv
cd /home/pi/led_strips && venv/bin/python -m unittest discover -s tests -v
```
- [ ] Tests pass on the Pi
- [ ] Copy in `network.cfg` and `config.json`, run `venv/bin/python led_interface.py` by hand,
      and check the Arduino frames (first LEDs correct), both Pixelblazes, audio, and image mode
- [ ] `venv/bin/python led_solid.py` works as a quick strip test
- [ ] Merge `python3-conversion` into `master`

### 4. Service instead of cron/PHP launching
- [ ] `led-strips.service`: `User=pi`, `WorkingDirectory=/home/pi/led_strips`,
      `ExecStart=/home/pi/led_strips/venv/bin/python led_interface.py`, `Restart=on-failure`.
      Commit the unit to the repo (for example `systemd/led-strips.service`).
- [ ] No `@reboot` crontab line; [startup.sh](startup.sh) / [start_from_server.sh](start_from_server.sh)
      are then only for running by hand
- [ ] Files the website touches must be reachable by `www-data`, and Trixie home dirs may be 0700.
      Either open `/home/pi` and the repo to traversal (`chmod o+x`) or move `config.json` and
      `status.log` to e.g. `/var/lib/led-strips/`, owned `pi:www-data`, mode 664.
      Paths: `CONFIG_FILE` in [set_config.py:17](set_config.py:17); `CONFIG_FILE` / `STATUS_FILE`
      in [led_interface.py:66](led_interface.py:66) (relative to `WorkingDirectory`). If `config.json`
      moves, give `set_config.py` a writable directory too, or it falls back to writing in place.
- [ ] sudoers rule (`visudo -f /etc/sudoers.d/led-strips`) so `www-data` can only run
      `systemctl start|stop led-strips.service`
- [ ] Volume: `www-data` in the `audio` group; PHP checks for an integer 0–100 before calling the volume script

### 5. Website on Apache 2.4 / PHP 8.4
- [ ] Commit the old web root to `christmas_led_site` first (see above), then clone it on the Pi
- [ ] `sudo apt install apache2 libapache2-mod-php`; keep the default `www-data` user
- [ ] Keep `.git` out of the served directory, or block it (`RedirectMatch 404 /\.git`)
- [ ] `status.php`: point it at the new `status.log` path. Allow a few seconds of slack:
      it says "Alive" only if the heartbeat is ≤1 s old, and the heartbeat is now written
      once a second, so it can flicker to "Dead".
- [ ] `start/index.php` → `sudo systemctl start|stop led-strips.service` instead of `kill` /
      `start_from_server.sh` (a second copy now exits anyway, because the serial port is exclusive)
- [ ] Turn the actions (start/stop, mode, volume) into POST requests with a CSRF token;
      today they're `$.get(...)` calls
- [ ] Stop printing the pid in `smallfooter.php`
- [ ] Remove dead bits: `start/start.py`, `patterns/patterns.py`, the `python3 music.py` /
      `python3 patterns.py` calls (the scripts don't exist or are empty); the missing
      `assets/img/banner-bg.jpg`; footer links to `/ieee/` and `/docs/resume.pdf`
- [ ] Disable `mod_status` and `autoindex` if unused
- [ ] Redirects use `header()` after HTML has been sent, which relies on PHP's
      default `output_buffering = 4096`. Keep it, or move the logic above the HTML.
- [ ] Nothing in the PHP is known to break on 8.4, but test every page

### 6. Going public (last)
- [ ] Domain on Cloudflare; `cloudflared` tunnel to `http://localhost:80`
- [ ] Login in front of the whole site (Cloudflare Access, or Apache basic auth over HTTPS)
- [ ] From a phone on cellular: login required, `/.git/` blocked, no open ports on the home IP
- [ ] Never expose SSH. Use Tailscale if remote SSH is wanted.

## Open questions
- Who should be able to control the lights: only invited people, or anyone who visits?
- Is there a domain already, and is moving its DNS to Cloudflare OK?
- What did the old crontab and sudoers actually contain, and was JACK running?
- Is there already a `led-strips.service` on the new Pi, and what does it contain?
