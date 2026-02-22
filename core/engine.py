"""
MashupID - Cross-Platform Engine
Paths, threading, and audio all work on Windows, Linux, macOS, Jetson Nano.
"""

import os
import sys
import platform
import threading
import time
import logging
import numpy as np
from typing import Optional, Callable, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.fingerprint import fingerprint_audio, SAMPLE_RATE
from core.database    import SongDatabase, MashupDetector
from core.audio       import AudioRecorder, load_audio_file

log = logging.getLogger("MashupID.Engine")

# Cross-platform default DB path
def _default_db() -> str:
    """
    Returns a sensible DB path on any OS:
      Windows : C:\\Users\\<user>\\AppData\\Local\\MashupID\\mashup_id.db
      Linux   : ~/.local/share/MashupID/mashup_id.db
      macOS   : ~/Library/Application Support/MashupID/mashup_id.db
    Falls back to script directory/songs_db/mashup_id.db
    """
    _os = platform.system()
    try:
        if _os == 'Windows':
            base = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
        elif _os == 'Darwin':
            base = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support')
        else:
            base = os.path.join(os.path.expanduser('~'), '.local', 'share')
        return os.path.join(base, 'MashupID', 'mashup_id.db')
    except Exception:
        here = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(here, '..', 'songs_db', 'mashup_id.db')


class MashupIDEngine:
    STATUS_IDLE      = "idle"
    STATUS_RECORDING = "recording"
    STATUS_ANALYZING = "analyzing"
    STATUS_DONE      = "done"
    STATUS_ERROR     = "error"

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = _default_db()
        # os.path.abspath handles both Windows backslashes and Unix slashes
        self.db_path = os.path.abspath(db_path)
        self.db       = SongDatabase(self.db_path)
        self.detector = MashupDetector(self.db)
        self.recorder = AudioRecorder(sample_rate=SAMPLE_RATE)

        self._status   = self.STATUS_IDLE
        self._progress = 0
        self._lock     = threading.Lock()
        self._thread:  Optional[threading.Thread] = None

        self._cb_status:   Optional[Callable] = None
        self._cb_progress: Optional[Callable] = None
        self._cb_result:   Optional[Callable] = None

        log.info(f"Engine started | OS={platform.system()} | DB={self.db_path}")

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def on_status(self,   cb: Callable): self._cb_status   = cb
    def on_progress(self, cb: Callable): self._cb_progress = cb
    def on_result(self,   cb: Callable): self._cb_result   = cb

    def on_audio_level(self, cb: Callable):
        self.recorder.set_level_callback(cb)

    def _emit_status(self, s: str, msg: str = ""):
        with self._lock:
            self._status = s
        if self._cb_status:
            self._cb_status(s, msg)

    def _emit_progress(self, p: int):
        with self._lock:
            self._progress = p
        if self._cb_progress:
            self._cb_progress(p)

    # ── Identify from microphone ──────────────────────────────────────────────

    def identify_from_microphone(self, duration: float = 10.0, mashup_mode: bool = False):
        if self._status in (self.STATUS_RECORDING, self.STATUS_ANALYZING):
            return

        def _run():
            try:
                self._emit_status(self.STATUS_RECORDING, f"Recording {duration:.0f}s…")
                self._emit_progress(0)

                self.recorder.start_recording()
                steps = int(duration * 10)
                for i in range(steps):
                    if self._status != self.STATUS_RECORDING:
                        break
                    time.sleep(0.1)
                    self._emit_progress(int((i + 1) / steps * 45))

                audio = self.recorder.stop_recording()
                if self._status == self.STATUS_IDLE:
                    return

                if audio is None or len(audio) < SAMPLE_RATE:
                    self._emit_status(self.STATUS_ERROR, "No audio captured")
                    return

                self._emit_status(self.STATUS_ANALYZING, "Analyzing…")
                result = self._analyze(audio, SAMPLE_RATE, mashup_mode,
                                       prog_start=45, prog_end=100,
                                       is_cancelled=lambda: self._status == self.STATUS_IDLE)
                self._emit_progress(100)
                self._emit_status(self.STATUS_DONE, "Complete")
                if self._cb_result:
                    self._cb_result(result)

            except Exception as e:
                log.exception("Identify error")
                self._emit_status(self.STATUS_ERROR, str(e))

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    # ── Identify from file ────────────────────────────────────────────────────

    def identify_from_file(self, filepath: str, mashup_mode: bool = False):
        if self._status in (self.STATUS_RECORDING, self.STATUS_ANALYZING):
            return

        def _run():
            try:
                name = os.path.basename(filepath)
                self._emit_status(self.STATUS_ANALYZING, f"Loading {name}…")
                self._emit_progress(10)

                audio, sr = load_audio_file(filepath, SAMPLE_RATE)
                if self._status == self.STATUS_IDLE:
                    return
                self._emit_progress(30)

                result = self._analyze(audio, sr, mashup_mode, 30, 100,
                                       is_cancelled=lambda: self._status == self.STATUS_IDLE)
                self._emit_progress(100)
                self._emit_status(self.STATUS_DONE, "Complete")
                if self._cb_result:
                    self._cb_result(result)

            except Exception as e:
                log.exception("File identify error")
                self._emit_status(self.STATUS_ERROR, str(e))

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    # ── Core analysis ─────────────────────────────────────────────────────────

    def _analyze(self, audio, sr, mashup_mode, prog_start, prog_end, is_cancelled=None):
        t0   = time.time()
        rng  = prog_end - prog_start

        if mashup_mode:
            def _prog(p):
                self._emit_progress(prog_start + int(p * rng / 100))
            result = self.detector.analyze(audio, sr, progress_cb=_prog, is_cancelled=is_cancelled)
        else:
            self._emit_progress(prog_start + rng // 2)
            fps     = fingerprint_audio(audio, sr, apply_noise_reduction=True)
            matches = self.db.query(fps, topn=5)
            result  = {
                'is_mashup': False,
                'total_duration': len(audio) / sr,
                'matches': matches,
                'timeline': [],
                'unique_songs': len(set(m.song_id for m in matches))
            }

        elapsed = time.time() - t0

        serial_matches = []
        for m in result.get('matches', []):
            serial_matches.append({
                'song_id':            m.song_id,
                'title':              m.title,
                'artist':             m.artist,
                'album':              m.album,
                'year':               m.year,
                'genre':              m.genre,
                'confidence':         round(m.confidence * 100, 1),
                'match_count':        m.match_count,
                'offset_seconds':     m.offset_seconds,
                'is_mashup_component': m.is_mashup_component,
                'cover_art_path':     m.cover_art_path,
            })

        res = {
            'success':        len(serial_matches) > 0,
            'is_mashup':      result.get('is_mashup', False),
            'total_duration': round(result.get('total_duration', 0), 2),
            'matches':        serial_matches,
            'timeline':       result.get('timeline', []),
            'unique_songs':   result.get('unique_songs', 0),
            'analysis_time':  round(elapsed, 2)
        }

        # Production History Logging
        try:
            best_sid = serial_matches[0]['song_id'] if serial_matches else None
            best_conf = serial_matches[0]['confidence'] if serial_matches else 0.0
            mode = "mashup" if mashup_mode else "standard"
            self.db.add_history_entry(res['success'], best_sid, best_conf, mode)
        except Exception as e:
            log.error(f"Failed to log history: {e}")

        return res

    def stop(self):
        """Cancels active recording or analysis by signalling the engine thread."""
        with self._lock:
            if self._status in (self.STATUS_RECORDING, self.STATUS_ANALYZING):
                self._status = self.STATUS_IDLE
                # We signal the recorder to stop but don't join here to avoid UI freeze
                self.recorder._recording = False 
                self._emit_status(self.STATUS_IDLE, "Stopping...")

    # ── Indexing ──────────────────────────────────────────────────────────────

    def index_song_file(
        self, filepath: str,
        title: str = "", artist: str = "", album: str = "",
        year: str = "", genre: str = "",
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        try:
            if not title:
                title = os.path.splitext(os.path.basename(filepath))[0]

            if progress_callback: progress_callback(10)
            audio, sr = load_audio_file(filepath, SAMPLE_RATE)
            duration  = len(audio) / sr

            if progress_callback: progress_callback(40)
            fps = fingerprint_audio(audio, sr, apply_noise_reduction=True)

            if progress_callback: progress_callback(80)
            song_id = self.db.add_song(
                title, artist, fps, album, year, duration, genre,
                file_path=filepath
            )

            if progress_callback: progress_callback(100)
            return {
                'success': True, 'song_id': song_id,
                'title': title, 'artist': artist,
                'fingerprints': len(fps), 'duration': round(duration, 2)
            }
        except Exception as e:
            log.exception("Index error")
            return {'success': False, 'error': str(e)}

    def index_directory(self, directory: str, progress_callback=None) -> Dict[str, Any]:
        supported = {'.wav', '.mp3', '.flac', '.ogg'}
        try:
            files = [
                os.path.join(directory, f)
                for f in os.listdir(directory)
                if os.path.splitext(f)[1].lower() in supported
            ]
        except Exception as e:
            return {'success': 0, 'failed': 0, 'error': str(e), 'songs': []}

        if not files:
            return {'total': 0, 'success': 0, 'failed': 0, 'songs': []}

        results = {'total': len(files), 'success': 0, 'failed': 0, 'songs': []}
        
        # For production, we still use index_song_file (which commits)
        # but we add error isolation so one bad file doesn't stop the whole batch.
        for i, fp in enumerate(files):
            try:
                r = self.index_song_file(fp)
                if r['success']:
                    results['success'] += 1
                    results['songs'].append(r)
                else:
                    results['failed'] += 1
            except Exception as e:
                log.error(f"Failed to index {fp}: {e}")
                results['failed'] += 1
                
            if progress_callback:
                progress_callback(int((i + 1) / len(files) * 100))
        return results

    # ── Helpers ───────────────────────────────────────────────────────────────

    def get_all_songs(self):   return self.db.get_all_songs()
    def delete_song(self, i):  return self.db.delete_song(i)
    def get_stats(self):       return self.db.get_stats()
    def get_status(self):      return self._status
    def get_progress(self):    return self._progress

    @property
    def has_microphone(self):  return self.recorder.has_microphone

    @property
    def audio_backend(self):   return self.recorder.backend
