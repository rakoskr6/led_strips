# setup/

Files for setting up the Raspberry Pi that runs the lights (Raspberry Pi OS 13 "Trixie"
Lite, repo at `/opt/led_strips`). [MIGRATION.md](../MIGRATION.md) has the full checklist;
this page explains what each piece is and how to use it day to day.

| File | Installed to | What it is |
|---|---|---|
| [led-strips.service](led-strips.service) | `/etc/systemd/system/led-strips.service` | Runs the lights at boot (see below) |
| [base-system.sh](base-system.sh) | run once with `sudo` | Updates, SSH keys only, firewall |
| [install-website.sh](install-website.sh) | run once with `sudo` | Apache + PHP and the website's access (see below) |
| [apache/led-site.conf](apache/led-site.conf) | `/etc/apache2/sites-available/led-site.conf` | The website: folder, what's hidden, logs |
| [apache/zz-led-site.conf](apache/zz-led-site.conf) | `/etc/apache2/conf-available/zz-led-site.conf` | Hides the Apache version |
| [apache/php-led-site.ini](apache/php-led-site.ini) | `/etc/php/8.4/apache2/conf.d/99-led-site.ini` | Hides the PHP version; safer session cookie |
| [sudoers-led-strips](sudoers-led-strips) | `/etc/sudoers.d/led-strips` | Lets the website start/stop the lights service, nothing else |
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

## The website (Apache)

The site is [christmas_led_site](https://github.com/rakoskr6/christmas_led_site), checked
out (as `krakos`) at `/var/www/christmas_led_site`. Apache serves it on port 80 to the home
network only (the firewall blocks everything else). Open `http://pi.local/` or the Pi's IP.
Apache runs PHP as the `www-data` user.

**How a button works.** Each page carries a random token tied to the visitor's session.
Buttons send a POST with that token to a small PHP file (`start/`, `lights_all/`,
`lights_tree/`, `lights_pattern/`, `options/volume.php`), which checks it and then runs one
command. Requests without the token are refused, so a link or another website can't work
the lights.

| Button | Runs (as `www-data`) |
|---|---|
| Start / Stop | `sudo systemctl start` / `stop led-strips.service` |
| Pattern mode | `set_config.py mode static` |
| Music mode (all / tree only) | `set_config.py wireless_music true` / `false`, then `set_config.py mode music` |
| Volume slider | `website_set_volume.sh <0-100>` (`amixer`) |

**What `www-data` is allowed to do**, set up by [install-website.sh](install-website.sh):
- read `status.log` and write `config.json` in `/opt/led_strips` (that folder and
  `config.json` are in group `www-data`; everything else there is read-only to it);
- run exactly the two `systemctl` commands above with `sudo` ([sudoers-led-strips](sudoers-led-strips));
- use the sound card's mixer (it's in the `audio` group).

**Everyday:**

| To | Run |
|---|---|
| Update the site after pushing changes | `cd /var/www/christmas_led_site && git pull` (no restart needed) |
| See errors from the PHP | `sudo tail -f /var/log/apache2/led-site-error.log` |
| See who visited | `sudo tail -f /var/log/apache2/led-site-access.log` |
| Restart Apache (after changing its config) | `sudo systemctl restart apache2` |
| Reinstall the config from this folder | `sudo bash /opt/led_strips/setup/install-website.sh` |

The `.git` folder, `README.md`, `.py` files and `lib.php` are never served (404), and there
are no folder listings.

Clicking a mode button rewrites `config.json`, so `git status` in `/opt/led_strips` shows it
as changed whenever the live settings differ from the repo. That's expected.

## Base system (SSH and firewall)

`sudo bash /opt/led_strips/setup/base-system.sh` installs updates and automatic security
updates, installs the SSH and firewall files above, and enables the firewall at boot. It can
be run again safely. Before saving the firewall, it asks you to open a *new* SSH session
to prove you can still get in, and it rolls the rules back after 120 s if you don't confirm.

SSH is open to the internet through a port forward on the router (see step 5b of
MIGRATION.md), with three layers on top of keys-only logins: only `krakos` may log in,
the firewall allows at most 4 new connections a minute per address, and sshd blocks
misbehaving addresses for longer each time (up to a day). The home network is exempt from
the blocking.

- See who's knocking: `journalctl -u ssh --since today`
- See addresses sshd is currently blocking: `sudo journalctl -u ssh --since today | grep -i penalty`
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
