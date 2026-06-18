## Raspberry Pi Install Notes

### Bookworm `pip` behavior

Raspberry Pi OS Bookworm may reject a normal editable install like:

```bash
python3 -m pip install -e .
```

with the `externally-managed-environment` error from PEP 668.

### Current manual workaround

For the current Pi workflow, use:

```bash
python3 -m pip install --break-system-packages -e .
```

Then continue with:

```bash
npm install
npm run build-css
sudo python3 -m piano_led web-serve --host 0.0.0.0 --port 8080 --with-live
```

### Follow-up for later

When we create the project install/setup script, it should explicitly handle this case.

Preferred future options:

- detect Bookworm / PEP 668 and use a project virtual environment, or
- if we intentionally stay on system Python, document and apply `--break-system-packages` in the script with clear warnings

The cleaner long-term direction is likely a dedicated project virtual environment plus updated service/run instructions.
