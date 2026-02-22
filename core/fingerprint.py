"""
MashupID - Core Audio Fingerprinting Engine
Cross-platform: Windows, Linux, macOS, Jetson Nano (ARM)
Pure numpy/scipy — no platform-specific dependencies
"""

import numpy as np
from scipy import signal
from scipy.ndimage import maximum_filter
import hashlib
import struct
from typing import List, Tuple

# ─── Constants ───────────────────────────────────────────────────────────────
SAMPLE_RATE       = 22050
WINDOW_SIZE       = 4096
HOP_SIZE          = 512
NUM_MEL_BINS      = 128
PEAK_NEIGHBORHOOD = 20
FAN_VALUE         = 15
MIN_TIME_DELTA    = 0
MAX_TIME_DELTA    = 200


# ─── Noise Reduction (Spectral Subtraction) ──────────────────────────────────

def reduce_noise(audio: np.ndarray, sr: int = SAMPLE_RATE) -> np.ndarray:
    """
    Robust non-stationary noise reduction.
    Optimized for noisy environments and ARM CPUs (Jetson Nano).
    """
    if len(audio) < 1024:
        return audio

    audio = audio.astype(np.float32)
    # Energy-based normalization
    rms = np.sqrt(np.mean(audio**2))
    if rms > 0:
        audio = audio / (rms * 10) # Target roughly 0.1 RMS
    
    frame_len = 1024 # Smaller frame for faster processing on ARM
    hop_len   = 256

    # 1. Spectral Subtraction
    _, _, Zxx = signal.stft(audio, fs=sr, nperseg=frame_len, noverlap=frame_len - hop_len)
    mag   = np.abs(Zxx)
    phase = np.angle(Zxx)

    # Multi-band noise estimation (estimate from quietest frames)
    # This is more robust than just taking the first 0.5s
    energies = np.sum(mag**2, axis=0)
    quiet_idx = np.argsort(energies)[:max(1, len(energies)//5)] # Quietest 20%
    noise_mag = np.mean(mag[:, quiet_idx], axis=1, keepdims=True)

    # Over-subtraction to aggressively target noise in mashups
    alpha = 3.0 # Over-subtraction factor
    beta  = 0.02 # Spectral floor
    
    mag_clean = np.maximum(mag - alpha * noise_mag, beta * noise_mag)
    
    # 2. Spectral Gating (Lightweight)
    # Suppress bins that are mostly noise
    gate = (mag_clean > (noise_mag * 1.5)).astype(np.float32)
    mag_clean *= gate

    Zxx_clean = mag_clean * np.exp(1j * phase)
    _, audio_clean = signal.istft(Zxx_clean, fs=sr, nperseg=frame_len, noverlap=frame_len - hop_len)
    audio_clean = audio_clean[: len(audio)]

    # 3. Band-pass filter (Focus on melody/rhythm: 100Hz - 8kHz)
    b, a = signal.butter(4, [100.0 / (sr / 2), 8000.0 / (sr / 2)], btype='band')
    audio_clean = signal.lfilter(b, a, audio_clean)

    # Final normalization
    max_val = np.max(np.abs(audio_clean))
    if max_val > 0:
        audio_clean = audio_clean / max_val

    return audio_clean.astype(np.float32)


# ─── Mel Spectrogram ─────────────────────────────────────────────────────────

def _hz_to_mel(hz: float) -> float:
    return 2595.0 * np.log10(1.0 + hz / 700.0)

def _mel_to_hz(mel: float) -> float:
    return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)

def _mel_filterbank(n_mels: int, n_fft: int, sr: int) -> np.ndarray:
    low_mel  = _hz_to_mel(80.0)
    high_mel = _hz_to_mel(sr / 2)
    mel_pts  = np.linspace(low_mel, high_mel, n_mels + 2)
    hz_pts   = np.array([_mel_to_hz(m) for m in mel_pts])
    bins     = np.floor((n_fft + 1) * hz_pts / sr).astype(int)

    fb = np.zeros((n_mels, n_fft // 2 + 1))
    for m in range(1, n_mels + 1):
        lo, mid, hi = bins[m - 1], bins[m], bins[m + 1]
        for k in range(lo, mid):
            if mid > lo:
                fb[m - 1, k] = (k - lo) / (mid - lo)
        for k in range(mid, hi):
            if hi > mid:
                fb[m - 1, k] = (hi - k) / (hi - mid)
    return fb

def compute_mel_spectrogram(audio: np.ndarray, sr: int = SAMPLE_RATE) -> np.ndarray:
    _, _, Zxx = signal.stft(
        audio, fs=sr, window='hann',
        nperseg=WINDOW_SIZE, noverlap=WINDOW_SIZE - HOP_SIZE
    )
    mag = np.abs(Zxx)
    fb  = _mel_filterbank(NUM_MEL_BINS, WINDOW_SIZE, sr)
    mel = np.dot(fb, mag)
    return 10.0 * np.log10(np.maximum(mel, 1e-10))


# ─── Peak Detection ──────────────────────────────────────────────────────────

def find_peaks(spec: np.ndarray, threshold_db: float = -25.0) -> List[Tuple[int, int]]:
    """Find constellation peaks in a dB-scale mel spectrogram."""
    local_max = maximum_filter(spec, size=PEAK_NEIGHBORHOOD)
    peaks_mask = (spec == local_max) & (spec > spec.max() + threshold_db)

    freq_idx, time_idx = np.where(peaks_mask)

    if len(freq_idx) == 0:
        # Fallback: top-500 strongest points
        flat    = spec.ravel()
        top_n   = min(500, len(flat))
        top_idx = np.argpartition(flat, -top_n)[-top_n:]
        freq_idx = top_idx // spec.shape[1]
        time_idx = top_idx % spec.shape[1]

    amps       = spec[freq_idx, time_idx]
    sorted_idx = np.argsort(-amps)[: min(500, len(amps))]
    return list(zip(freq_idx[sorted_idx].tolist(), time_idx[sorted_idx].tolist()))


# ─── Hash Generation ─────────────────────────────────────────────────────────

def generate_fingerprints(peaks: List[Tuple[int, int]]) -> List[Tuple[str, int]]:
    """Combinatorial Shazam-style hashes from constellation peaks."""
    fingerprints = []
    peaks_by_time = sorted(peaks, key=lambda x: x[1])

    for i, (f1, t1) in enumerate(peaks_by_time):
        for j in range(1, FAN_VALUE + 1):
            if i + j < len(peaks_by_time):
                f2, t2 = peaks_by_time[i + j]
                dt = t2 - t1
                if MIN_TIME_DELTA <= dt <= MAX_TIME_DELTA:
                    raw = struct.pack('>IIH', f1, f2, int(dt))
                    h   = hashlib.sha1(raw).hexdigest()[:16]
                    fingerprints.append((h, t1))

    return fingerprints


# ─── Full Pipeline ────────────────────────────────────────────────────────────

def fingerprint_audio(
    audio: np.ndarray,
    sr: int = SAMPLE_RATE,
    apply_noise_reduction: bool = True
) -> List[Tuple[str, int]]:
    """
    Full fingerprinting pipeline:
      audio → noise reduction → mel spectrogram → peaks → hashes
    """
    if len(audio) == 0:
        return []

    if apply_noise_reduction:
        audio = reduce_noise(audio, sr)

    mel   = compute_mel_spectrogram(audio, sr)
    peaks = find_peaks(mel)

    if not peaks:
        return []

    return generate_fingerprints(peaks)
