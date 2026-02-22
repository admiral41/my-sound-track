# Sabdha Desktop — Cross-Platform Guide
> Offline song & mashup identifier | Windows · Linux · macOS · Jetson Nano

---

## Windows — Quick Start (3 steps)

### Step 1: Install Python
Download from **https://www.python.org/downloads/** (Python 3.10 or 3.11 recommended)

>  During installation, **check "Add Python to PATH"** — this is critical!

### Step 2: Run the app
Double-click `START_WINDOWS.bat` and choose option **[1] Run app NOW**

### Step 3 (optional): Build .exe
Double-click `START_WINDOWS.bat` and choose **[2] Build .exe**  
→ Creates `dist\MashupID.exe` — a single file you can run on any Windows PC

---

##  Linux / Jetson Nano — Quick Start

```bash
# Make launcher executable
chmod +x START_LINUX.sh

# Run it
./START_LINUX.sh
# Choose [1] to run, or [2] to build binary
```

Or manually:
```bash
# Install dependencies
sudo apt-get install -y libportaudio2 python3-pip
pip3 install PyQt6 numpy scipy sounddevice

# Run app
python3 main.py

# Or build binary
python3 -m PyInstaller MashupID.spec --clean
./dist/MashupID
```

---

## macOS — Quick Start

```bash
chmod +x START_LINUX.sh && ./START_LINUX.sh

# Or manually:
brew install portaudio
pip3 install PyQt6 numpy scipy sounddevice pyinstaller
python3 main.py
```

---

## Build Single Executable (all platforms)

The universal build script works everywhere:

```bash
# Full setup + build in one command:
python setup_and_build.py

# Just install deps:
python setup_and_build.py --deps

# Just build (deps already installed):
python setup_and_build.py --build

# Add demo songs:
python setup_and_build.py --demo
```

Output files:
| Platform | Output |
|---|---|
| Windows  | `dist\MashupID.exe` (~180 MB) |
| Linux    | `dist/MashupID`    (~150 MB) |
| macOS    | `dist/MashupID.app`           |

---

## Manual Dependency Install

### Windows (Command Prompt / PowerShell)
```batch
# Install Python packages
pip install PyQt6 numpy scipy sounddevice pyinstaller

# For microphone support on Windows (try in order):
pip install pipwin
pipwin install pyaudio

# OR direct:
pip install pyaudio

# Build
python -m PyInstaller MashupID.spec --clean
```

### Linux (Ubuntu / Debian / Jetson Nano)
```bash
# System packages
sudo apt-get install -y libportaudio2 portaudio19-dev python3-pip

# Python packages
pip3 install PyQt6 numpy scipy sounddevice pyinstaller

# Build
python3 -m PyInstaller MashupID.spec --clean
```

### Jetson Nano (JetPack)
```bash
# JetPack already has numpy/scipy
sudo apt-get install -y libportaudio2 portaudio19-dev

# PyQt6 may need a specific version for aarch64
pip3 install PyQt6 sounddevice pyinstaller

python3 main.py   # Run directly
# OR
python3 -m PyInstaller MashupID.spec --clean
```

---

## Project Structure

```
mashupid_cross/
├── main.py                 ← Full PyQt6 desktop app
├── setup_and_build.py      ← Universal setup/build (all platforms)
├── MashupID.spec           ← PyInstaller config
├── START_WINDOWS.bat       ← Double-click launcher for Windows
├── START_LINUX.sh          ← Shell launcher for Linux/macOS
├── core/
│   ├── fingerprint.py      ← Shazam algorithm (pure numpy/scipy)
│   ├── database.py         ← SQLite matching engine
│   ├── audio.py            ← Cross-platform mic + file loading
│   └── engine.py           ← Thread-safe orchestrator
└── songs_db/
    └── mashup_id.db        ← Auto-created SQLite DB
```

---

## 🎙 Microphone Support by Platform

| Platform | Backend | Notes |
|---|---|---|
| Windows 10/11 | sounddevice or pyaudio | Both auto-tried |
| Ubuntu / Debian | sounddevice | Needs `libportaudio2` |
| Jetson Nano | sounddevice | USB mic works great |
| macOS | sounddevice | Needs Homebrew portaudio |
| No mic | simulate mode | UI still works, file-only |

---

## Database Location (auto-detected per OS)

| OS | Database Path |
|---|---|
| Windows | `%LOCALAPPDATA%\MashupID\mashup_id.db` |
| Linux   | `~/.local/share/MashupID/mashup_id.db` |
| macOS   | `~/Library/Application Support/MashupID/mashup_id.db` |

---

## Add Songs (First Time)

1. Launch the app
2. Click **Add Songs** in the sidebar
3. Click **Browse** → select a WAV file
4. Fill in Title + Artist → **⚡ Index Song**

**Or use the CLI** (great for batch adding):
```bash
# Add demo songs for testing
python setup_and_build.py --demo

# Then launch
python main.py
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` not found on Windows | Install Python, check "Add to PATH" |
| `PyQt6` install fails | `pip install PyQt6==6.4.2` (older stable version) |
| No microphone detected | App shows warning, use file mode |
| `PortAudio library not found` | Linux: `sudo apt-get install libportaudio2` |
| Build takes too long | Normal — first build is 3-6 min |
| Antivirus blocks .exe | False positive — add to exclusions |
| Dark theme looks wrong | App uses Fusion style — works on all platforms |

---

## Supported Audio Formats

| Format | Support |
|---|---|
| `.wav` |  Native — always works |
| `.mp3` |  Needs `pip install pydub` + ffmpeg |
| `.flac` |  Needs `pip install soundfile` |

**Convert to WAV with ffmpeg (easiest):**
```bash
# Windows (if ffmpeg is installed)
ffmpeg -i song.mp3 -ar 22050 -ac 1 song.wav

# Linux
ffmpeg -i song.mp3 -ar 22050 -ac 1 song.wav
```
