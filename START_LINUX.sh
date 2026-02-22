#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#  MashupID — Linux / macOS / Jetson Nano Launcher
# ═══════════════════════════════════════════════════════════════════

set -e
cd "$(dirname "$0")"

OS="$(uname -s)"
ARCH="$(uname -m)"

echo ""
echo " ╔══════════════════════════════════════════════════╗"
echo " ║       MashupID — Linux/macOS Setup & Launcher     ║"
echo " ╚══════════════════════════════════════════════════╝"
echo ""
echo " Platform: $OS / $ARCH"

# ── Install system dependencies ─────────────────────────────────────
if [[ "$OS" == "Linux" ]]; then
    echo " Installing system packages..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get install -y libportaudio2 portaudio19-dev python3-pip 2>/dev/null || true
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y portaudio-devel python3-pip 2>/dev/null || true
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm portaudio python-pip 2>/dev/null || true
    fi
elif [[ "$OS" == "Darwin" ]]; then
    if command -v brew &>/dev/null; then
        brew install portaudio 2>/dev/null || true
    fi
fi

# ── Python check ─────────────────────────────────────────────────────
# Try to find a suitable Python version (3.9+)
PY=""
for cmd in python3.11 python3.10 python3.9 python3; do
    if command -v "$cmd" &>/dev/null; then
        VERSION=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        MAJOR=$(echo $VERSION | cut -d. -f1)
        MINOR=$(echo $VERSION | cut -d. -f2)
        if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 9 ]; then
            PY=$(command -v "$cmd")
            break
        fi
    fi
done

if [[ -z "$PY" ]]; then
    # Fallback to whatever python3 is if no 3.9+ found (script will likely fail later)
    PY=$(command -v python3 || command -v python)
fi

echo " Python: $($PY --version) [Using: $PY]"

# ── Install Python packages ───────────────────────────────────────────
echo " Installing Python packages..."
$PY -m pip install PyQt6 numpy scipy sounddevice pyinstaller --quiet --upgrade

# ── Menu ──────────────────────────────────────────────────────────────
echo ""
echo " Choose an option:"
echo "  [1] Run app NOW  (no build, run with Python)"
echo "  [2] Build binary (creates dist/MashupID)"
echo "  [3] Create demo songs"
echo "  [4] Exit"
echo ""
read -p " Enter choice (1-4): " choice

case $choice in
  1)
    echo " Starting MashupID..."
    $PY main.py
    ;;
  2)
    echo " Building executable..."
    $PY -m PyInstaller MashupID.spec --clean --noconfirm
    if [[ -f "dist/MashupID" ]]; then
        chmod +x dist/MashupID
        SIZE=$(du -sh dist/MashupID | cut -f1)
        echo ""
        echo " ✅  Built: dist/MashupID  ($SIZE)"
        echo " 🚀  Run:   ./dist/MashupID"
    fi
    ;;
  3)
    $PY setup_and_build.py --demo
    ;;
  *)
    echo " Goodbye."
    ;;
esac
