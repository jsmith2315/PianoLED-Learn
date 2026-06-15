# Stage 01 - Realtime Piano to LED

## Goal

Light the mapped LED immediately when a note is pressed.

## Before testing this repo on the Pi

If the old project is still installed and auto-starting, stop it first so it does not keep control of MIDI ports or the LED strip.

The old project installer creates a systemd service named `visualizer.service`.

Stop it for the current boot:

```bash
sudo systemctl stop visualizer.service
```

Prevent it from auto-starting on reboot:

```bash
sudo systemctl disable visualizer.service
```

Check whether it is still running:

```bash
systemctl status visualizer.service --no-pager
sudo journalctl -u visualizer.service -n 50 --no-pager
```

If you want to make sure it cannot be started accidentally while we test this repo:

```bash
sudo systemctl mask visualizer.service
```

Later, if you want to restore it:

```bash
sudo systemctl unmask visualizer.service
sudo systemctl enable visualizer.service
sudo systemctl start visualizer.service
```

## Build checklist

- parse note on/off events
- resolve note to LED index through the active keymap
- use a different black-key color when enabled
- clear LEDs on note release
- expose clear-strip and chase-test actions

## Success criteria

- note on lights the expected LED
- note off clears the expected LED
- black keys can use a separate color

## Pi smoke-test commands for this repo

After pulling the new code to the Pi, start with:

```bash
python3 -m unittest discover -s tests -t . -v
python3 -m piano_led
python3 -m piano_led midi-list-ports
python3 -m piano_led led-chase --steps 10
python3 -m piano_led led-clear
```

When the live MIDI backend is configured in `data/settings/settings.json`, use:

```bash
python3 -m piano_led midi-monitor
```
