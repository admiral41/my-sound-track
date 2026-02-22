"""
MashupID - Cross-Platform Audio Module
Supports: Windows (sounddevice/pyaudio), Linux, macOS, Jetson Nano
Gracefully falls back to file-only mode if no microphone found.
"""

import os
import sys
import wave
import struct
import threading
import time
import platform
import numpy as np
from scipy import signal
from typing import Optional, Callable, Tuple, List

SAMPLE_RATE = 22050
CHANNELS    = 1
CHUNK_SIZE  = 4096

# Detect OS once
_OS = platform.system()  # 'Windows', 'Linux', 'Darwin'


# ─── WAV File I/O ─────────────────────────────────────────────────────────────

def load_wav(filepath: str, target_sr: int = SAMPLE_RATE) -> Tuple[np.ndarray, int]:
    """
    Load WAV file on any OS.
    Uses only stdlib wave module — no ffmpeg or external tools needed.
    """
    with wave.open(filepath, 'rb') as wf:
        n_channels  = wf.getnchannels()
        sample_width = wf.getsampwidth()
        frame_rate  = wf.getframerate()
        n_frames    = wf.getnframes()
        raw         = wf.readframes(n_frames)

    dtype_map = {1: np.uint8, 2: np.int16, 4: np.int32}
    dtype = dtype_map.get(sample_width, np.int16)
    audio = np.frombuffer(raw, dtype=dtype).astype(np.float32)

    if sample_width == 1:
        audio = audio / 128.0 - 1.0
    elif sample_width == 2:
        audio = audio / 32768.0
    elif sample_width == 4:
        audio = audio / 2147483648.0

    if n_channels > 1:
        audio = audio.reshape(-1, n_channels).mean(axis=1)

    if frame_rate != target_sr:
        audio = _resample(audio, frame_rate, target_sr)

    return audio.astype(np.float32), target_sr


def save_wav(filepath: str, audio: np.ndarray, sr: int = SAMPLE_RATE):
    """Save numpy array as WAV — cross-platform using stdlib only."""
    audio_i16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(filepath, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_i16.tobytes())


def _resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr:
        return audio
    target_len = int(len(audio) * target_sr / orig_sr)
    return signal.resample(audio, target_len).astype(np.float32)


def load_audio_file(filepath: str, target_sr: int = SAMPLE_RATE) -> Tuple[np.ndarray, int]:
    """
    Universal audio loader — tries multiple backends:
    1. WAV:  stdlib wave (always works)
    2. FLAC/OGG: soundfile (needs libsndfile, already on Ubuntu)
    3. MP3/any: pydub (needs ffmpeg)
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == '.wav':
        return load_wav(filepath, target_sr)

    # Try soundfile (works for FLAC, OGG, and some MP3)
    # libsndfile is usually pre-installed: sudo apt install libsndfile1
    try:
        import soundfile as sf
        audio, sr = sf.read(filepath, dtype='float32', always_2d=False)
        if audio.ndim == 2:              # stereo -> mono
            audio = audio.mean(axis=1)
        if sr != target_sr:
            audio = _resample(audio, sr, target_sr)
        return audio.astype(np.float32), target_sr
    except Exception:
        pass

    # Try pydub (optional — needs ffmpeg installed separately)
    try:
        from pydub import AudioSegment
        seg = AudioSegment.from_file(filepath)
        seg = seg.set_channels(1).set_frame_rate(target_sr).set_sample_width(2)
        samples = np.array(seg.get_array_of_samples(), dtype=np.float32) / 32768.0
        return samples, target_sr
    except Exception:
        pass

    raise ValueError(
        "Cannot load '{}'. Supported: WAV (always), FLAC/OGG (install: pip install soundfile), "
        "MP3 (install ffmpeg + pydub). Quickest fix: convert to WAV first:\n"
        "  ffmpeg -i input.mp3 -ar 22050 -ac 1 output.wav".format(os.path.basename(filepath))
    )


# ─── Audio Backend Detection ──────────────────────────────────────────────────

def _detect_backend() -> str:
    """Detect the best available audio capture backend."""
    # 1. sounddevice — works on Windows/Linux/macOS with PortAudio
    try:
        import sounddevice as sd
        devs = sd.query_devices()
        for d in devs:
            if d['max_input_channels'] > 0:
                return 'sounddevice'
    except Exception:
        pass

    # 2. pyaudio — older but very widely supported on Windows
    try:
        import pyaudio
        pa = pyaudio.PyAudio()
        count = pa.get_device_count()
        pa.terminate()
        if count > 0:
            return 'pyaudio'
    except Exception:
        pass

    # 3. Windows-specific: winsound can't record, but check for other options
    if _OS == 'Windows':
        # Try soundcard library
        try:
            import soundcard as sc
            mics = sc.all_microphones()
            if mics:
                return 'soundcard'
        except Exception:
            pass

    return 'simulate'


# ─── Audio Recorder ───────────────────────────────────────────────────────────

class AudioRecorder:
    """
    Cross-platform microphone recorder.
    Tries backends in order: sounddevice → pyaudio → soundcard → simulate
    """

    def __init__(self, sample_rate: int = SAMPLE_RATE, chunk_size: int = CHUNK_SIZE):
        self.sample_rate = sample_rate
        self.chunk_size  = chunk_size
        self._buffer: List[np.ndarray] = []
        self._recording = False
        self._thread: Optional[threading.Thread] = None
        self._level_cb: Optional[Callable] = None
        self._backend = _detect_backend()

    @property
    def backend(self) -> str:
        return self._backend

    @property
    def has_microphone(self) -> bool:
        return self._backend != 'simulate'

    def set_level_callback(self, cb: Callable):
        self._level_cb = cb

    def get_devices(self) -> List[dict]:
        """List available input devices (cross-platform)."""
        devices = []
        try:
            import sounddevice as sd
            for i, d in enumerate(sd.query_devices()):
                if d['max_input_channels'] > 0:
                    devices.append({
                        'index': i,
                        'name':  d['name'],
                        'channels': d['max_input_channels'],
                        'sample_rate': int(d['default_samplerate']),
                        'backend': 'sounddevice'
                    })
        except Exception:
            pass

        if not devices:
            try:
                import pyaudio
                pa = pyaudio.PyAudio()
                for i in range(pa.get_device_count()):
                    info = pa.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        devices.append({
                            'index': i,
                            'name': info['name'],
                            'channels': info['maxInputChannels'],
                            'sample_rate': int(info['defaultSampleRate']),
                            'backend': 'pyaudio'
                        })
                pa.terminate()
            except Exception:
                pass

        if not devices:
            devices = [{'index': 0, 'name': 'Default Microphone',
                        'channels': 1, 'sample_rate': SAMPLE_RATE, 'backend': self._backend}]
        return devices

    def start_recording(self):
        self._buffer   = []
        self._recording = True
        self._thread   = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop_recording(self) -> Optional[np.ndarray]:
        self._recording = False
        if self._thread:
            self._thread.join(timeout=0.1)
        if not self._buffer:
            return None
        return np.concatenate(self._buffer).astype(np.float32)

    def _run(self):
        try:
            dispatch = {
                'sounddevice': self._record_sounddevice,
                'pyaudio':     self._record_pyaudio,
                'soundcard':   self._record_soundcard,
                'simulate':    self._record_simulate,
            }
            func = dispatch.get(self._backend, self._record_simulate)
            func()
        except Exception as e:
            # Device recovery attempt
            print(f"Audio backend error ({self._backend}): {e}")
            if self._backend != 'simulate' and self._recording:
                print("Falling back to simulation mode...")
                self._backend = 'simulate'
                self._record_simulate()
            else:
                self._recording = False

    def _push(self, chunk: np.ndarray):
        self._buffer.append(chunk)
        if self._level_cb:
            level = float(np.abs(chunk).mean())
            self._level_cb(level)

    def _record_sounddevice(self):
        try:
            import sounddevice as sd

            def callback(indata, frames, time_info, status):
                if not self._recording:
                    raise sd.CallbackAbort()
                self._push(indata[:, 0].copy())

            with sd.InputStream(
                samplerate=self.sample_rate, channels=1,
                dtype='float32', blocksize=self.chunk_size,
                callback=callback
            ):
                while self._recording:
                    time.sleep(0.05)
        except Exception:
            self._record_simulate()

    def _record_pyaudio(self):
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            # Try float32 first; fall back to int16 for Windows devices that
            # don't support float capture
            fmt = pyaudio.paFloat32
            try:
                stream = pa.open(
                    format=fmt, channels=1, rate=self.sample_rate,
                    input=True, frames_per_buffer=self.chunk_size
                )
            except Exception:
                fmt = pyaudio.paInt16
                stream = pa.open(
                    format=fmt, channels=1, rate=self.sample_rate,
                    input=True, frames_per_buffer=self.chunk_size
                )
            while self._recording:
                try:
                    raw = stream.read(self.chunk_size, exception_on_overflow=False)
                    if fmt == pyaudio.paFloat32:
                        chunk = np.frombuffer(raw, dtype=np.float32).copy()
                    else:
                        chunk = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                    self._push(chunk)
                except Exception:
                    break
            stream.stop_stream()
            stream.close()
            pa.terminate()
        except Exception:
            self._record_simulate()

    def _record_soundcard(self):
        try:
            import soundcard as sc
            mic = sc.default_microphone()
            sr  = self.sample_rate
            with mic.recorder(samplerate=sr, channels=1) as r:
                while self._recording:
                    chunk = r.record(numframes=self.chunk_size).flatten()
                    self._push(chunk.astype(np.float32))
        except Exception:
            self._record_simulate()

    def _record_simulate(self):
        """
        Demo mode when no microphone is connected.
        Generates realistic-looking audio so the UI still works.
        """
        sr   = self.sample_rate
        dur  = self.chunk_size / sr
        t    = 0.0
        phase = 0.0
        while self._recording:
            phase += 0.08
            amp   = 0.15 * abs(np.sin(phase))
            chunk = np.zeros(self.chunk_size, dtype=np.float32)
            freqs = [440, 880, 1320, 2640]
            tt    = np.linspace(t, t + dur, self.chunk_size, endpoint=False)
            for f in freqs:
                chunk += np.sin(2 * np.pi * f * tt).astype(np.float32) * amp * 0.3
            chunk += np.random.randn(self.chunk_size).astype(np.float32) * 0.04
            self._push(chunk)
            t += dur
            time.sleep(dur * 0.9)
