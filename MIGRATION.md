# Migration: Raspbian 9 (Stretch) → Raspberry Pi OS 13 (Trixie)

Hand-off notes for moving the LED lights and their control website from the old
SD card to a fresh Trixie install on the same Raspberry Pi 3 Model B. Based on a
review of a file-level backup of the old card plus the `python3-conversion`
branch. Items marked **unverified** need checking on the Pi.

This repo is public, so local IPs, Wi-Fi details, key names and other private
details are deliberately left out. They live in `network.cfg` and on the old card.

## Status (2026-11-23)

- New Pi: Trixie Lite, user `krakos`, packages updated, `git` installed, this repo
  cloned to `/opt/led_strips` on `python3-conversion`, `network.cfg` copied over,
  SSH key login working.
- Step 1 (base system) done with [setup/base-system.sh](setup/base-system.sh), including a fixed IP and Wi-Fi off.
- Step 2 (audio) done remotely: card detected, mixer restored, capture works. The line-in test with
  real audio and the reboot check moved to step 5a, for when someone is at the Pi.
- Step 3 (LED code) done remotely: venv built, tests pass, `led_interface.py` runs against the
  Arduino (no LEDs attached). Watching the lights and the Pixelblazes (off for now) moved to step 5a.
- Step 4 done: the lights run as `led-strips.service` (systemd), enabled at boot.
- Step 5 done: Apache + PHP serve the site to the home network; actions are POST + CSRF token
  and start/stop goes through systemd. Browser check from another device is in step 5a.
- **Deferred:** everything internet-facing (step 6). No router ports are forwarded.

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

The lights now run as a systemd service; the unit file is [setup/led-strips.service](setup/led-strips.service) (step 4).

## Decisions

- Fresh Trixie **Lite** install, user `krakos`, Ethernet only.
- The repo lives in **`/opt/led_strips`**, not a home folder, so nothing depends on
  the login name and Apache can reach it. The scripts find their files relative to
  their own folder; only the website PHP needs the full path.
- Python 3 from apt plus a `--system-site-packages` venv at `/opt/led_strips/venv`;
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
  `master` now holds the live site from the old Pi (it had never been committed;
  GitHub only had a Dec 2020 version), with its paths already pointing at
  `/opt/led_strips`.

**Not in git, copy from the old card/backup**
- [x] `~/led_strips/network.cfg` (Pixelblaze addresses; gitignored; format in [README.md](README.md)), copied
- `~/led_strips/config.json` (live settings; differs from git)
- [x] `/usr/share/doc/audioInjector/asound.state.RCA.thru.test` (the mixer state restored at boot), now in [setup/alsa/](setup/alsa/)
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
Run from your own SSH terminal: `sudo bash /opt/led_strips/setup/base-system.sh`.
It does the first three items below. It applies the firewall live and rolls it back
after 120 s unless you confirm that a new SSH session still gets in.

- [x] `apt full-upgrade`, `unattended-upgrades` installed and enabled
      (Debian security updates only; Raspberry Pi kernel/firmware updates still need a manual `apt full-upgrade`)
- [x] SSH keys only: [setup/sshd-10-local.conf](setup/sshd-10-local.conf) → `/etc/ssh/sshd_config.d/10-local.conf`.
      It must sort before Imager's `50-cloud-init.conf`, because sshd keeps the first value it reads.
      Also turns off root login and X11 forwarding.
- [x] Firewall: [setup/nftables.conf](setup/nftables.conf) → `/etc/nftables.conf`, `nftables.service` enabled.
      Default drop inbound; SSH (22) and HTTP (80) from private addresses only, plus ICMP, DHCP and mDNS.
      Covers IPv6 too, which matters because the Pi has public IPv6 addresses.
- [x] Fixed IP for the Pi's Ethernet, set on the AT&T gateway (Home Network → IP Allocation)
- [x] `krakos` in `dialout` and `audio` groups (already set by Imager)
- [x] `git` installed, repo cloned to `/opt/led_strips` (owned by `krakos`)
- [x] GitHub SSH key (`~/.ssh/id_ed25519`); GitHub's host key checked against its published fingerprint;
      `origin` switched to `git@github.com:rakoskr6/led_strips.git`
- [x] Wi-Fi off: saved connection deleted (`nmcli`), radio off, Wi-Fi removed from Imager's
      first-boot `/boot/firmware/network-config` (it held the password in plain text),
      `dtoverlay=disable-wifi` added under `[all]` in `config.txt` (applies at the next reboot;
      the old file is `config.txt.bak`)

### 2. Audio (riskiest part)
Done before the reboot:
- [x] `/boot/firmware/config.txt`: `dtparam=audio=off`, `dtoverlay=vc4-kms-v3d,noaudio`
      (so HDMI audio doesn't take a card slot), `dtoverlay=audioinjector-wm8731-audio` under `[all]`
      (next to `disable-wifi`). The old `pi3-disable-bt` / `enable_uart=0` are not carried over;
      the Arduino is on USB, not the UART. Imager's original is `config.txt.bak`.
- [x] The overlay ships with Trixie (`/boot/firmware/overlays/audioinjector-wm8731-audio.dtbo`),
      so the 2017 Audio Injector `.deb` in [README.md](README.md) isn't needed
- [x] Default ALSA device set **by name** in [setup/alsa/asound.conf](setup/alsa/asound.conf) →
      `/etc/asound.conf` (system-wide, not `~/.asoundrc`, so `www-data`'s volume scripts use the card too)
- [x] The `.deb`'s mixer states are in [setup/alsa/](setup/alsa/): `asound.state.RCA.thru.test`
      (line-in, what the old Pi restored at boot) and `asound.state.MIC.thru.test`
- [x] `alsa-utils` installed (Lite includes it)

After the reboot (2026-11-23):
- [x] `aplay -l` / `arecord -l` show only the Audio Injector, id `audioinjectorpi`; `wlan0` gone
- [x] Mixer: `sudo alsactl --file /opt/led_strips/setup/alsa/asound.state.RCA.thru.test restore 0`,
      then `sudo alsactl store 0`. Input Mux is `Line In`, Capture 23/31 (74%).
      The `failed to import hw:0 use case configuration` message is harmless (no UCM profile for this card).
- [x] `amixer sget 'Capture'` works; [website_get_volume.sh](website_get_volume.sh) reads 74 and
      [website_set_volume.sh](website_set_volume.sh) sets it (50 reads back as 52: the control has 31 steps)
- [x] Capture at 32 kHz, 2 channels, S16 works, and so does full duplex (record + play at once,
      as `led_interface.py` does). The input was silent, so the line-in path itself is still untested (step 5a).
- JACK not installed; nothing needs it so far.

The remaining audio checks need someone at the Pi and are in step 5a.

### 3. LED code on the hardware
```bash
sudo apt install python3-venv python3-numpy python3-scipy python3-pil python3-serial python3-websocket python3-pyaudio
python3 -m venv --system-site-packages /opt/led_strips/venv
cd /opt/led_strips && venv/bin/python -m unittest discover -s tests -v
```
Done remotely (2026-11-23):
- [x] apt packages and venv installed: Python 3.13.5, NumPy 2.2.4, SciPy 1.15.3, Pillow 11.1.0,
      pyserial 3.5, websocket-client 1.8.0, PyAudio 0.2.13
- [x] Tests pass on the Pi: 34 run, 1 skipped (it compares against the removed `colour` library)
- [x] PyAudio opens the stream the way `led_interface.py` does (float32, 32 kHz, 2 ch, in + out)
      and gets steady callbacks. The `JackShmReadWritePtr` / "Cannot connect to server" lines are
      PortAudio probing for JACK; harmless.
- [x] Arduino Mega present as `/dev/ttyACM0` (group `dialout`, which `krakos` is in)
- [x] With the Arduino connected but no LEDs on it: `led_solid.py` gets `Program Started` and runs
      without write timeouts. `led_interface.py` finds the Arduino, resyncs it, starts audio,
      writes `status.log` every second, and keeps running with the Pixelblazes unreachable
      (it retries every 30 s). A second copy exits ("Could not exclusively lock port"), and
      `SIGTERM` stops it cleanly (exit 0, port released).
- [x] `network.cfg` copied. Its leftover `[phue]` section is unused and harmless.
- Both Pixelblazes are switched off for now, so they couldn't be reached; checked in step 5a.
- The repo's `config.json` is used for now; compare it with the old Pi's in step 5a.

The checks that need someone watching the lights are in step 5a. Merge
`python3-conversion` into `master` after those pass.

### 4. Run the lights as a service (done 2026-11-23)

The lights now run as a systemd service instead of being started by cron and the website.
The service starts them at boot and restarts them 5 s after a crash, but leaves them
stopped after a deliberate `systemctl stop`. **What that means, everyday commands, and
troubleshooting are in [setup/README.md](setup/README.md).** The unit file is
[setup/led-strips.service](setup/led-strips.service), installed to `/etc/systemd/system/`.

**Checked:**
- [x] No crontab lines to remove (none for `krakos` or root on the new Pi)
- [x] Installed, enabled at boot, running: finds the Arduino, starts audio, writes `status.log`
      every second with the service's own PID
- [x] Killed with `kill -9` → restarted by systemd 5 s later
- [x] `systemctl stop` → stops cleanly, frees the serial port, and stays stopped
- [x] About 30% of one CPU core and 100 MB of memory on the Pi 3; 46 °C
- [ ] Starts on its own after a reboot (checked with the reboot in step 5a)

### 5. Website on Apache 2.4 / PHP 8.4 (done 2026-11-23)
Set up by [setup/install-website.sh](setup/install-website.sh); how it works and everyday
commands are in [setup/README.md](setup/README.md#the-website-apache).

Server (Apache 2.4.71, PHP 8.4.28):
- [x] `apache2` + `libapache2-mod-php` installed; Apache runs as `www-data`
- [x] Site cloned (as `krakos`) to `/var/www/christmas_led_site`, served by
      [setup/apache/led-site.conf](setup/apache/led-site.conf); Debian's default site disabled
- [x] `.git`, `README.md`, `.py` files and `lib.php` return 404; `autoindex` and `status`
      modules disabled; Apache and PHP versions hidden; session cookie `HttpOnly`, `SameSite=Strict`

What the website may do with the lights:
- [x] `www-data` can read `status.log` and write `config.json`, and can't change anything
      else in `/opt/led_strips` (folder and `config.json` in group `www-data`, folder setgid).
      It can't create files there, so [set_config.py](set_config.py) writes `config.json`
      in place when the website runs it. That's expected.
- [x] `/etc/sudoers.d/led-strips`: `www-data` may run only
      `systemctl start|stop led-strips.service`
- [x] `www-data` in the `audio` group, for the volume scripts

The PHP ([christmas_led_site `369945b`](https://github.com/rakoskr6/christmas_led_site)):
- [x] Paths point at `/opt/led_strips/`
- [x] New `lib.php`: session + CSRF token, status, running commands without a shell.
      "Alive" now allows 5 s of slack (was 1 s, which flickered to "Dead").
- [x] Start/stop uses `sudo systemctl start|stop led-strips.service` and asks for
      start or stop explicitly, instead of toggling with `kill` / `start_from_server.sh`
- [x] All actions (start/stop, modes, volume) are POSTs with the CSRF token; GET → 405,
      bad or missing token → 403. Volume must be a whole number 0–100.
- [x] Mode buttons post and show the result instead of navigating away
- [x] Footer shows "Lights: Alive/Dead" without the pid
- [x] Removed `start/start.py`, `patterns/patterns.py`, the `python3 music.py` /
      `patterns.py` calls (`music/` and `patterns/` now redirect home), `status.php`,
      the missing `banner-bg.jpg`, footer links to `/ieee/` and `/docs/resume.pdf`
- [x] Redirects come before any HTML, so they don't rely on `output_buffering`
- [x] Tested with `curl` on the Pi: every page 200 with no PHP warnings, `/nope` → 404,
      all refusals, all three modes change `config.json`, volume sets `amixer`,
      start/stop drive the service, nothing in the error log
- [ ] Try it from a phone or PC browser on the home network (step 5a)

Left as they were (not part of the migration):
- The Options page's Brightness slider and Pattern / Colour buttons are mock-ups that do nothing.
- `assets/dark-bootstrap/` (8.4 MB) and `assets/backup/` aren't used by any page.
- Font Awesome and Google Fonts load from the internet.

### 5a. Hands-on checks (deferred until someone is at the Pi)
- [ ] Line-in with real audio: play music into the RCA input and record
      (`arecord -D default -f S16_LE -r 32000 -c 2 -d 5 /tmp/test.wav`); expect clearly more than silence
      on both channels. Compare the lights' response with the old Pi and adjust Capture if needed
      (then `sudo alsactl store 0`).
- [ ] `sudo reboot`, then check `amixer sget 'Capture'` and `amixer sget 'Input Mux'` still read
      74% / `Line In` (alsa-utils restoring `/var/lib/alsa/asound.state`), and that
      `systemctl status led-strips` shows it started on its own. Can be done remotely.
- [ ] Install JACK only if the lights turn out to need it (not expected)
- [ ] Pixelblazes on and reachable at the addresses in `network.cfg` (IP reservations on the gateway)
- [ ] LEDs plugged into the Arduino; `venv/bin/python led_solid.py` fades them blue, green, red
- [ ] Run the lights (the service from step 4, or `venv/bin/python led_interface.py` by hand) and check:
      first LEDs the right colour, both Pixelblazes, audio response, image mode
- [ ] Compare `config.json` with the old Pi's live copy (on the old card at
      `/home/pi/led_strips/config.json`) and carry over any settings worth keeping
- [ ] The website from a phone or PC on the home network: every page, Start/Stop, the three
      modes, the volume slider
- [ ] Then merge `python3-conversion` into `master`

### 6. Going public (last; deferred, no ports forwarded yet)
- [ ] Domain on Cloudflare; `cloudflared` tunnel to `http://localhost:80`
- [ ] Login in front of the whole site (Cloudflare Access, or Apache basic auth over HTTPS)
- [ ] From a phone on cellular: login required, `/.git/` blocked, no open ports on the home IP
- [ ] Never expose SSH. Use Tailscale if remote SSH is wanted.

## Open questions
- Who should be able to control the lights: only invited people, or anyone who visits?
- Is there a domain already, and is moving its DNS to Cloudflare OK?
- What did the old crontab and sudoers actually contain, and was JACK running?
