#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SERVICE_USER="${1:-${SUDO_USER:-${USER:-$(id -un)}}}"
PROJECT_DIR="${2:-$DEFAULT_PROJECT_DIR}"
SERVICE_PATH="/etc/systemd/system/piano-led-live.service"

sudo tee "$SERVICE_PATH" >/dev/null <<EOF
[Unit]
Description=Piano LED Learn Live Runtime
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/python3 -m piano_led run-live
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable piano-led-live.service
sudo systemctl restart piano-led-live.service

echo "Installed piano-led-live.service for user '$SERVICE_USER' using project dir '$PROJECT_DIR'."
