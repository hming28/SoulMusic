#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${SOULMUSIC_REPO:-https://github.com/hming28/SoulMusic.git}"
ZIP_URL="${SOULMUSIC_ZIP_URL:-https://github.com/hming28/SoulMusic/archive/refs/heads/main.tar.gz}"
INSTALL_DIR="${SOULMUSIC_DIR:-$HOME/SoulMusic}"
NO_LAUNCH="${SOULMUSIC_NO_LAUNCH:-0}"

echo "=========================================="
echo "  SoulMusic One-Command Installer"
echo "=========================================="
echo "Install directory: $INSTALL_DIR"

# 1. Check Python 3.9+
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required (3.9+). Please install Python 3 first." >&2
  exit 1
fi

python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' || {
  echo "ERROR: Python 3.9+ is required." >&2
  exit 1
}

# 2. Download or update repository
if command -v git >/dev/null 2>&1; then
  if [ -d "$INSTALL_DIR/.git" ]; then
    echo "[1/3] Updating existing SoulMusic repository..."
    if [ -z "$(git -C "$INSTALL_DIR" status --porcelain)" ]; then
      git -C "$INSTALL_DIR" pull --ff-only
    else
      echo "  Local changes detected; skipping git pull."
    fi
  else
    echo "[1/3] Cloning SoulMusic..."
    git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
  fi
else
  echo "[1/3] Git not found; downloading tarball..."
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TMP_DIR"' EXIT
  curl -fsSL "$ZIP_URL" | tar -xz -C "$TMP_DIR"
  EXTRACTED_DIR="$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
  mkdir -p "$INSTALL_DIR"
  cp -R "$EXTRACTED_DIR"/. "$INSTALL_DIR"/
fi

# 3. Setup virtual environment & dependencies
echo "[2/3] Setting up virtual environment and dependencies..."
VENV_DIR="$INSTALL_DIR/.venv"
if [ ! -x "$VENV_DIR/bin/python" ]; then
  python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip --quiet
"$VENV_DIR/bin/python" -m pip install -r "$INSTALL_DIR/requirements.txt"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "Note: ffmpeg not found in PATH. Install it via brew/apt for faster audio demuxing."
fi

# 4. Launch
echo "[3/3] Done! Installed at $INSTALL_DIR"
if [ "$NO_LAUNCH" != "1" ]; then
  cd "$INSTALL_DIR"
  exec "$VENV_DIR/bin/python" "$INSTALL_DIR/soulmusic.py"
fi
