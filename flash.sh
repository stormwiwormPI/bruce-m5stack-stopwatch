#!/usr/bin/env sh
# Bruce Firmware flasher for the M5Stack StopWatch (ESP32-S3).
# All real work happens in flash.py so Windows / Linux / macOS behave the same.

set -e
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "  [XX] Python 3 was not found."
    echo "       Install it with your package manager, e.g.:"
    echo "         macOS        brew install python"
    echo "         Debian/Ubuntu sudo apt install python3 python3-pip"
    echo "         Fedora       sudo dnf install python3"
    exit 1
fi

exec "$PY" flash.py "$@"
