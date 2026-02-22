# -*- mode: python ; coding: utf-8 -*-
# ════════════════════════════════════════════════════════
#  MashupID.spec  —  Universal PyInstaller build config
#  Works for:  Windows (.exe)  |  Linux (binary)  |  macOS (.app)
#
#  Build command (same on all platforms):
#    pyinstaller MashupID.spec --clean
#
#  Output:
#    Windows  →  dist\MashupID.exe
#    Linux    →  dist/MashupID
#    macOS    →  dist/MashupID.app
# ════════════════════════════════════════════════════════

import sys
import os
import platform

_OS   = platform.system()
_HERE = os.path.dirname(os.path.abspath(SPEC))   # noqa: F821  (SPEC is PyInstaller built-in)

block_cipher = None

# ── Collect all source files ─────────────────────────────────────────────────
a = Analysis(
    ['main.py'],
    pathex=[_HERE],
    binaries=[],
    datas=[
        # Include songs_db folder (will be empty on first run, DB created at runtime)
        (os.path.join(_HERE, 'songs_db'), 'songs_db'),
    ],
    hiddenimports=[
        # Numpy / Scipy internals (sometimes not auto-detected)
        'numpy',
        'numpy.core._multiarray_umath',
        'numpy.core._multiarray_tests',
        'numpy.lib.format',
        'scipy',
        'scipy.signal',
        'scipy.signal._signaltools',
        'scipy.signal.windows',
        'scipy.signal.windows._windows',
        'scipy.ndimage',
        'scipy.ndimage._filters',
        'scipy.ndimage._interpolation',
        'scipy.ndimage._measurements',
        'scipy.ndimage._morphology',
        'scipy.ndimage._ni_support',
        'scipy.io',
        'scipy.io.wavfile',
        'scipy.fft',
        'scipy._lib.messagestream',
        'scipy.special._ufuncs_cxx',
        'scipy.linalg.cython_blas',
        'scipy.linalg.cython_lapack',
        'scipy.integrate._quad_vec',

        # Audio backends — include all, use whatever is installed
        'sounddevice',
        'pyaudio',
        'soundcard',

        # SQLite (stdlib but sometimes needs explicit inclusion)
        'sqlite3',
        '_sqlite3',

        # PyQt6 modules
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        'PyQt6.QtOpenGL',

        # Standard library
        'wave',
        'struct',
        'hashlib',
        'threading',
        'queue',
        'json',
        'logging',
        'logging.handlers',
        'dataclasses',
        'collections',
        'collections.abc',
        'ctypes',
        'ctypes.util',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Things we don't use — keep the binary smaller
        'matplotlib',
        'PIL', 'Pillow',
        'tkinter', '_tkinter',
        'wx',
        'tensorflow', 'torch', 'keras',
        'sklearn', 'scikit_learn',
        'pandas', 'IPython', 'notebook', 'jupyter',
        'sympy', 'cvxpy',
        'gi', 'dbus',            # Linux GUI libs we don't need
        'pydoc', 'doctest',
        'test', 'unittest',
        'distutils',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── EXE / Binary ─────────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MashupID',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,          # Compress (smaller file). Set False if UPX not installed.
    upx_exclude=[
        'vcruntime140.dll',    # Don't compress Windows runtime DLLs
        'python3*.dll',
        'Qt6*.dll',
    ],
    runtime_tmpdir=None,
    console=False,     # False = no black terminal window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,  # None = current arch (x86_64, arm64, etc.)
    codesign_identity=None,
    entitlements_file=None,

    # ── Icon (optional) ──────────────────────────────────────────────────────
    # Windows: icon='assets/icon.ico'
    # macOS:   icon='assets/icon.icns'
    # Linux:   icon not used
    icon=None,

    # ── Single-file bundle ───────────────────────────────────────────────────
    onefile=True,      # Everything in ONE file. Change to False for faster startup.
)

# ── macOS .app bundle (only created on macOS) ────────────────────────────────
if _OS == 'Darwin':
    app = BUNDLE(
        exe,
        name='MashupID.app',
        icon=None,   # Replace with 'assets/icon.icns'
        bundle_identifier='com.mashupid.app',
        info_plist={
            'CFBundleName':        'MashupID',
            'CFBundleDisplayName': 'MashupID',
            'CFBundleVersion':     '1.0.0',
            'NSMicrophoneUsageDescription':
                'MashupID uses the microphone to identify songs.',
            'NSHighResolutionCapable': True,
        },
    )
