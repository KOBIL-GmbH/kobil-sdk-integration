#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
python3 claude-install/install.py
printf '\nPress Enter to close. '
read -r answer
