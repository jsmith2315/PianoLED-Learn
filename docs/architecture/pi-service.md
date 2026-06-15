# Pi Live Service

## Purpose

This service runs the new project in its normal live piano-to-LED mode on the Pi.

It uses:

- the configured MIDI input from `data/settings/settings.json`
- the configured LED backend from `data/settings/settings.json`
- the `run-live` CLI command

## Service installer

The repo includes a small installer script at:

- `deploy/systemd/install-pi-service.sh`

It writes a user-specific service file with the correct `User=` and
`WorkingDirectory=` values for your Pi account.

## Install on the Pi

From the project root on the Pi:

```bash
bash deploy/systemd/install-pi-service.sh <your-user> /home/<your-user>/PianoLED-Learn
```

## Check status and logs

```bash
systemctl status piano-led-live.service --no-pager
sudo journalctl -u piano-led-live.service -n 100 --no-pager
```

## Stop or disable

```bash
sudo systemctl stop piano-led-live.service
sudo systemctl disable piano-led-live.service
```

## Development note

Commands like `python3 -m piano_led status` and `python3 -m piano_led midi-list-ports`
avoid real LED initialization, so they are safer to run while diagnosing Pi setup.

## Local settings override

The repo-tracked file `data/settings/settings.json` should stay safe for development
defaults such as fake backends.

Machine-specific Pi settings belong in:

- `data/settings/settings.local.json`
- see `data/settings/settings.local.example.json` for a starting point

When present, the app loads `settings.json` first and then overlays values from
`settings.local.json`. Runtime saves also go back to `settings.local.json`, which
helps your LED and MIDI configuration survive future `git pull` operations.
