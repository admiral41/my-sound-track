#!/usr/bin/env python3
"""
MashupID — Universal Setup & Build Script
Run this ONE script on ANY platform to install dependencies and build the executable.

Usage:
    python setup_and_build.py          # Install deps + build
    python setup_and_build.py --deps   # Install deps only
    python setup_and_build.py --build  # Build only
    python setup_and_build.py --demo   # Create demo database
    python setup_and_build.py --run    # Run without building
"""

import sys
import os
import subprocess
import platform
import argparse

_OS   = platform.system()   # 'Windows', 'Linux', 'Darwin'
_ARCH = platform.machine()  # 'x86_64', 'aarch64', 'AMD64', 'arm64'
_PY   = sys.executable

BANNER = r"""
 ███╗   ███╗ █████╗ ███████╗██╗  ██╗██╗   ██╗██████╗ ██╗██████╗ 
 ████╗ ████║██╔══██╗██╔════╝██║  ██║██║   ██║██╔══██╗██║██╔══██╗
 ██╔████╔██║███████║███████╗███████║██║   ██║██████╔╝██║██║  ██║
 ██║╚██╔╝██║██╔══██║╚════██║██╔══██║██║   ██║██╔═══╝ ██║██║  ██║
 ██║ ╚═╝ ██║██║  ██║███████║██║  ██║╚██████╔╝██║     ██║██████╔╝
 ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚═════╝ 
 Offline Mashup Song Identifier — Cross-Platform Build Tool
"""

def run(cmd, **kwargs):
    """Run a shell command, exit on failure."""
    print(f"\n  ▶  {cmd}\n")
    result = subprocess.run(cmd, shell=True, **kwargs)
    if result.returncode != 0:
        print(f"\n  ❌  Command failed (exit {result.returncode})")
        sys.exit(result.returncode)
    return result


def pip(*packages, optional=False):
    """Install pip packages."""
    for pkg in packages:
        cmd = f'"{_PY}" -m pip install "{pkg}" --quiet --upgrade'
        r = subprocess.run(cmd, shell=True)
        if r.returncode != 0:
            if optional:
                print(f"  ⚠  Optional package '{pkg}' failed to install — skipping")
            else:
                print(f"  ❌  Failed to install required package: {pkg}")
                sys.exit(1)


def check_python():
    major, minor = sys.version_info[:2]
    print(f"  Python {major}.{minor} on {_OS} / {_ARCH}")
    if major < 3 or (major == 3 and minor < 9):
        print("  ❌  Python 3.9+ required")
        sys.exit(1)
    print("  ✅  Python version OK")


def install_system_deps():
    """Install OS-level audio dependencies."""
    print("\n  ── System Dependencies ──────────────────────────────")

    if _OS == 'Linux':
        # Check if PortAudio is installed
        r = subprocess.run("dpkg -l libportaudio2 2>/dev/null | grep -q '^ii'",
                           shell=True)
        if r.returncode != 0:
            print("  Installing PortAudio (needed for microphone support)…")
            run("sudo apt-get install -y libportaudio2 portaudio19-dev 2>/dev/null || "
                "sudo yum install -y portaudio-devel 2>/dev/null || true")
        else:
            print("  ✅  PortAudio already installed")

    elif _OS == 'Darwin':
        # macOS — PortAudio via Homebrew
        r = subprocess.run("which brew", shell=True, capture_output=True)
        if r.returncode == 0:
            subprocess.run("brew install portaudio 2>/dev/null || true", shell=True)
        else:
            print("  ⚠  Homebrew not found. If microphone fails: brew install portaudio")

    elif _OS == 'Windows':
        # Windows — sounddevice bundles PortAudio DLL automatically via pip
        print("  ✅  Windows: PortAudio is bundled with sounddevice (no extra install needed)")


def install_python_deps():
    """Install all Python packages."""
    print("\n  ── Python Packages ──────────────────────────────────")

    # Core scientific packages
    print("  Installing numpy, scipy (legacy versions for 3.6)…")
    pip("numpy<1.20", "scipy<1.6")

    # GUI framework
    print("  Installing PyQt5…")
    pip("PyQt5")

    # Audio capture — sounddevice is the best cross-platform option
    print("  Installing sounddevice…")
    pip("sounddevice", optional=True)

    # pyaudio as fallback (Windows sometimes needs it)
    if _OS == 'Windows':
        print("  Installing pyaudio (Windows fallback)…")
        # pipwin makes pyaudio easy on Windows
        pip("pipwin", optional=True)
        r = subprocess.run(f'"{_PY}" -m pipwin install pyaudio', shell=True)
        if r.returncode != 0:
            pip("pyaudio", optional=True)

    # Builder
    print("  Installing pyinstaller…")
    pip("pyinstaller")

    # Optional: MP3/FLAC support
    print("  Installing pydub (optional — for MP3/FLAC)…")
    pip("pydub", optional=True)

    print("  ✅  All packages installed")


def build_executable():
    """Run PyInstaller to create the executable."""
    print("\n  ── Building Executable ──────────────────────────────")

    os.makedirs("songs_db", exist_ok=True)
    os.makedirs("dist",     exist_ok=True)

    cmd = f'"{_PY}" -m PyInstaller MashupID.spec --clean --noconfirm'
    run(cmd)

    # Check output
    exe_path = os.path.join("dist", "MashupID.exe" if _OS == 'Windows' else "MashupID")
    app_path = os.path.join("dist", "MashupID.app")

    if _OS == 'Darwin' and os.path.isdir(app_path):
        print(f"\n  ✅  BUILD COMPLETE!")
        print(f"  📦  Output: {app_path}")
        print(f"  🚀  Run:    open '{app_path}'")
    elif os.path.isfile(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\n  ✅  BUILD COMPLETE!")
        print(f"  📦  Output: {exe_path}  ({size_mb:.0f} MB)")
        if _OS == 'Windows':
            print(f"  🚀  Run:    .\\dist\\MashupID.exe")
        else:
            print(f"  🚀  Run:    ./dist/MashupID")
            os.chmod(exe_path, 0o755)
    else:
        print("  ❌  Build failed — output file not found")
        print(f"      Expected: {exe_path}")
        sys.exit(1)


def create_demo():
    """Add demo songs to the database for testing."""
    print("\n  ── Creating Demo Database ────────────────────────────")
    import numpy as np
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from core.fingerprint import fingerprint_audio
    from core.database    import SongDatabase

    # Platform-aware default DB path
    if _OS == 'Windows':
        db_dir = os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'MashupID')
    elif _OS == 'Darwin':
        db_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'MashupID')
    else:
        db_dir = os.path.join(os.path.expanduser('~'), '.local', 'share', 'MashupID')
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, 'mashup_id.db')

    print(f"  DB: {db_path}")
    db = SongDatabase(db_path)
    sr = 22050

    demos = [
        ("Bohemian Rhapsody",  "Queen",         "A Night at the Opera", "1975", "Rock",     354, 10),
        ("Blinding Lights",    "The Weeknd",     "After Hours",          "2019", "Synthpop", 200, 20),
        ("God's Plan",         "Drake",          "Scorpion",             "2018", "Hip-Hop",  198, 30),
        ("Shape of You",       "Ed Sheeran",     "Divide",               "2017", "Pop",      234, 40),
        ("Rolling in the Deep","Adele",          "21",                   "2010", "Soul",     228, 50),
        ("Lose Yourself",      "Eminem",         "8 Mile",               "2002", "Hip-Hop",  326, 60),
        ("Stairway to Heaven", "Led Zeppelin",   "Led Zeppelin IV",      "1971", "Rock",     482, 70),
        ("Superstition",       "Stevie Wonder",  "Talking Book",         "1972", "Funk",     245, 80),
    ]

    for title, artist, album, year, genre, dur, seed in demos:
        np.random.seed(seed)
        t = np.linspace(0, min(dur, 30), sr * min(dur, 30))
        hv = abs(hash(f"{title}{artist}")) % 700
        audio = np.zeros(len(t), dtype=np.float32)
        for f in [200 + hv, 400 + hv//2, 800 + hv//4, 1600 + hv//8]:
            env = np.abs(np.sin(2 * np.pi * 0.3 * t)) + 0.2
            audio += np.sin(2 * np.pi * f * t).astype(np.float32) * env * 0.3
        audio += np.random.randn(len(t)).astype(np.float32) * 0.06
        audio = (audio / np.max(np.abs(audio))).astype(np.float32)
        fps = fingerprint_audio(audio, sr, apply_noise_reduction=False)
        db.add_song(title, artist, fps, album, year, float(dur), genre)
        print(f"  ✅  {title} — {artist}  ({len(fps)} fingerprints)")

    stats = db.get_stats()
    print(f"\n  🎉  Demo ready: {stats['total_songs']} songs, {stats['total_fingerprints']:,} fingerprints")
    print(f"  📁  DB: {db_path}")


def run_app():
    """Run the app directly with Python (no build needed)."""
    print("\n  🚀  Starting MashupID…")
    os.execv(_PY, [_PY, os.path.join(os.path.dirname(__file__), "main.py")])


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(BANNER)
    print(f"  Platform: {_OS} / {_ARCH}")
    print(f"  Python:   {sys.version.split()[0]}")
    print()

    p = argparse.ArgumentParser(
        description="MashupID cross-platform setup & build tool"
    )
    p.add_argument("--deps",  action="store_true", help="Install dependencies only")
    p.add_argument("--build", action="store_true", help="Build executable only")
    p.add_argument("--demo",  action="store_true", help="Create demo database")
    p.add_argument("--run",   action="store_true", help="Run app (no build)")
    args = p.parse_args()

    if args.run:
        run_app()
        return

    if args.demo:
        create_demo()
        return

    # Default: full setup + build
    do_deps  = args.deps  or (not args.build)
    do_build = args.build or (not args.deps)

    check_python()

    if do_deps:
        install_system_deps()
        install_python_deps()

    if do_build:
        build_executable()

    print("\n  ════════════════════════════════════════════════════")
    print("  Run demo setup:   python setup_and_build.py --demo")
    print(f"  Run the app:       {'dist\\MashupID.exe' if _OS == 'Windows' else './dist/MashupID'}")
    print("  ════════════════════════════════════════════════════\n")


if __name__ == "__main__":
    main()
