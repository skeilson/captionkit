#!/usr/bin/env bash
# CaptionKit installer.
#
# Run once from inside the cloned captionkit folder:
#   ./install.sh
#
# What it does:
#   1. Checks for Python 3.10+ with Tkinter
#   2. On macOS, installs PortAudio (needed for microphone access) via Homebrew
#   3. Creates a virtual environment in .venv and installs requirements.txt into it
#   4. Copies config.example.yaml to config.yaml if you don't have one yet
#
# It never overwrites an existing config.yaml, so it's safe to re-run.

set -euo pipefail

cd "$(dirname "$0")"

echo ""
echo "=== CaptionKit install ==="
echo ""

# --- Python 3.10+ ---
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install it from https://www.python.org/downloads/"
  exit 1
fi

if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "ERROR: Python 3.10 or newer is required (found $(python3 --version))."
  exit 1
fi
echo "Python: $(python3 --version)"

# --- Tkinter (used for the windows) ---
if ! python3 -c 'import tkinter' >/dev/null 2>&1; then
  echo "ERROR: Tkinter is missing from this Python."
  echo "  python.org installer: Tkinter is included; reinstall from python.org."
  echo "  Homebrew Python:      brew install python-tk"
  exit 1
fi

# --- PortAudio (macOS) ---
if [[ "$(uname)" == "Darwin" ]]; then
  if ! command -v brew >/dev/null 2>&1; then
    echo "ERROR: Homebrew not found. Install it from https://brew.sh, then re-run."
    exit 1
  fi
  if brew list portaudio >/dev/null 2>&1; then
    echo "PortAudio: already installed"
  else
    echo "Installing PortAudio..."
    brew install portaudio
  fi
fi

# --- Virtual environment + dependencies ---
if [[ ! -d .venv ]]; then
  echo "Creating virtual environment in .venv..."
  python3 -m venv .venv
fi

echo "Installing Python packages (this can take a few minutes)..."
.venv/bin/python -m pip install --upgrade pip --quiet
.venv/bin/python -m pip install -r requirements.txt --quiet

# --- Config ---
if [[ -f config.yaml ]]; then
  echo "config.yaml: keeping your existing file"
else
  cp config.example.yaml config.yaml
  echo "config.yaml: created from config.example.yaml"
fi

echo ""
echo "=== Done ==="
echo ""
echo "Start CaptionKit with:"
echo "  .venv/bin/python main.py"
echo ""
echo "The first run downloads the speech model, which can take a minute."
echo ""
