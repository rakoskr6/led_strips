# setup/

Files for setting up the Raspberry Pi that runs the lights (Raspberry Pi OS 13 "Trixie"
Lite, repo at `/opt/led_strips`). [MIGRATION.md](../MIGRATION.md) has the full checklist;
this page explains what each piece is and how to use it day to day.

| File | Installed to | What it is |
|---|---|---|
| [led-strips.service](led-strips.service) | `/etc/systemd/system/led-strips.service` | Runs the lights at boot (see below) |
| [base-system.sh](base-system.sh) | run once with `sudo` | Updates, SSH keys only, firewall |
| [sshd-10-local.conf](sshd-10-local.conf) | `/etc/ssh/sshd_config.d/10-local.conf` | SSH: keys only, no root login |
| [nftables.conf](nftables.conf) | `/etc/nftables.conf` | Firewall: SSH and HTTP from the home network only |
| [alsa/asound.conf](alsa/asound.conf) | `/etc/asound.conf` | Makes the Audio Injector card the default sound device |
| [alsa/asound.state.RCA.thru.test](alsa/asound.state.RCA.thru.test) | loaded with `alsactl` | Mixer settings for line-in (RCA) |
| [alsa/asound.state.MIC.thru.test](alsa/asound.state.MIC.thru.test) | loaded with `alsactl` | Mixer settings for the microphone input (not used) |

## The lights service (systemd)

### What it is

**systemd** is the part of Linux that starts everything at boot (SSH, the network,
the firewall) and keeps it running. Each thing it runs is a **service**, described by a
short text file called a *unit*. [led-strips.service](led-strips.service) is the unit for
the lights. It tells systemd to:

- run `venv/bin/python led_interface.py` in `/opt/led_strips`, as the `krakos` user (not root);
- start it at every boot, after the sound card's mixer settings are restored and the network is up;
- start it again 5 seconds after it crashes or exits with an error (for example when the
  Arduino is unplugged), and never give up;
- leave it stopped if someone stops it on purpose (`systemctl stop`);
- keep it out of home folders and stop it from changing system files.

Before this, a cron `@reboot` line started the lights and nothing restarted them after a
crash. The website started and stopped them by running scripts and `kill`. Once step 5 of
the migration is done, it uses `systemctl` instead.

Everything the program prints goes to the system log (the **journal**), not to a screen
or a file.

### Everyday commands

| To | Run |
|---|---|
| See if it's running, plus its last few log lines | `systemctl status led-strips` |
| Stop it | `sudo systemctl stop led-strips` |
| Start it | `sudo systemctl start led-strips` |
| Restart it (after changing the Python code or `network.cfg`) | `sudo systemctl restart led-strips` |
| Watch the log live | `journalctl -u led-strips -f` (Ctrl+C to quit) |
| Log since the last boot | `journalctl -u led-strips -b` |
| Log for the last hour | `journalctl -u led-strips --since "1 hour ago"` |
| Don't start it at boot any more | `sudo systemctl disable led-strips` |
| Start it at boot again | `sudo systemctl enable led-strips` |

`config.json` is re-read while the program runs, so changing settings (from the website
or with `set_config.py`) doesn't need a restart.

### Running things by hand

Only one program at a time can use the Arduino's serial port. To run `led_solid.py`, or
`led_interface.py` in a terminal to see its output directly, stop the service first:

```bash
sudo systemctl stop led-strips
cd /opt/led_strips && venv/bin/python led_solid.py     # Ctrl+C to quit
sudo systemctl start led-strips
```

If you forget, the second copy exits straight away with
`Could not exclusively lock port /dev/ttyACM0`.

### Installing or changing the unit

The copy systemd uses is the one in `/etc/systemd/system/`, not the one in the repo.
After editing [led-strips.service](led-strips.service), install it again:

```bash
sudo cp /opt/led_strips/setup/led-strips.service /etc/systemd/system/
sudo systemctl daemon-reload            # tell systemd the file changed
sudo systemctl enable --now led-strips  # start at boot, and start now
sudo systemctl restart led-strips       # if it was already running
```

`systemd-analyze verify setup/led-strips.service` checks the file for mistakes first.

### When something's wrong

- **Lights off, service "active (running)":** the program is up but something it talks to
  isn't. Look at `journalctl -u led-strips -b` for Pixelblaze timeouts, serial write
  timeouts ("resyncing the Arduino") or "Waiting for audio" (no sound on line-in).
- **Service "activating (auto-restart)" over and over:** the program keeps crashing.
  The journal shows why. An unplugged Arduino looks like this, and it recovers by itself
  once the Arduino is back.
- **Service "inactive (dead)":** someone stopped it, or it isn't enabled. Run
  `sudo systemctl start led-strips`, and `systemctl is-enabled led-strips` to check boot.

## Base system (SSH and firewall)

`sudo bash /opt/led_strips/setup/base-system.sh` installs updates and automatic security
updates, installs the SSH and firewall files above, and enables the firewall at boot. It can
be run again safely. Before saving the firewall, it asks you to open a *new* SSH session
to prove you can still get in, and it rolls the rules back after 120 s if you don't confirm.

- Check the live firewall: `sudo nft list ruleset`
- Allow another port from the home network: add it to both `tcp dport { 22, 80 }` lines
  in [nftables.conf](nftables.conf) and run the script again.

## Audio (ALSA)

ALSA is the Linux sound system. The card shows up as `audioinjectorpi`
(`arecord -l` lists it). To put the line-in mixer settings back and keep them across reboots:

```bash
sudo alsactl --file /opt/led_strips/setup/alsa/asound.state.RCA.thru.test restore 0
sudo alsactl store 0      # saved to /var/lib/alsa/asound.state, restored at every boot
```

`amixer sget 'Capture'` shows the input volume, which the website changes.
