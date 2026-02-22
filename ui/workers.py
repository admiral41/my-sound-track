"""
MashupID - Background Worker Threads
"""

import threading
from PyQt5.QtCore import QThread, pyqtSignal
from core.engine import MashupIDEngine

class IdentifyWorker(QThread):
    sig_progress = pyqtSignal(int)
    sig_status   = pyqtSignal(str, str)
    sig_result   = pyqtSignal(dict)
    sig_level    = pyqtSignal(float)

    def __init__(self, engine: MashupIDEngine, mode: str, duration: float, filepath: str = ""):
        super().__init__()
        self.engine   = engine
        self.mode     = mode
        self.duration = duration
        self.filepath = filepath
        self._done    = threading.Event()
        self._result  = None

    def run(self):
        try:
            # Register callbacks which emit signals (thread-safe)
            self.engine.on_status(lambda s, m: self.sig_status.emit(s, m))
            self.engine.on_progress(lambda p: self.sig_progress.emit(p))
            self.engine.on_audio_level(lambda l: self.sig_level.emit(float(l)))
            self.engine.on_result(self._got_result)

            if self.filepath:
                self.engine.identify_from_file(
                    self.filepath, mashup_mode=(self.mode == "mashup"))
            else:
                self.engine.identify_from_microphone(
                    self.duration, mashup_mode=(self.mode == "mashup"))

            # Calculate a safe timeout: record time + analysis buffer + extra safety
            # Mashup mode takes longer due to sliding window analysis
            buffer = 15 if self.mode == "mashup" else 8
            if not self._done.wait(timeout=self.duration + buffer):
                self.sig_status.emit("error", "Analysis timed out. Try again.")
                self.sig_result.emit({"success": False, "error": "Timeout", "matches": []})
            elif self._result:
                self.sig_result.emit(self._result)
            
        except Exception as e:
            self.sig_status.emit("error", f"Worker error: {str(e)}")
            self.sig_result.emit({"success": False, "error": str(e), "matches": []})
        finally:
            # Cleanup callbacks to prevent leakage
            self.engine.on_status(None)
            self.engine.on_progress(None)
            self.engine.on_audio_level(None)
            self.engine.on_result(None)

    def _got_result(self, r):
        self._result = r
        self._done.set()

    def stop(self):
        """Forces the worker to stop waiting."""
        self._done.set()


class SingleIndexWorker(QThread):
    sig_progress = pyqtSignal(int)
    sig_done     = pyqtSignal(dict)

    def __init__(self, engine, fp, title, artist, album, year, genre):
        super().__init__()
        self.engine = engine
        self.args   = (fp, title, artist, album, year, genre)

    def run(self):
        # Runs synchronously in this thread
        r = self.engine.index_song_file(*self.args,
                                        progress_callback=self.sig_progress.emit)
        self.sig_done.emit(r)


class BatchIndexWorker(QThread):
    sig_progress = pyqtSignal(int)
    sig_done     = pyqtSignal(dict)

    def __init__(self, engine, directory):
        super().__init__()
        self.engine = engine
        self.directory = directory

    def run(self):
        # Runs synchronously in this thread
        # Passing sig_progress.emit is thread-safe: it posts event to main thread
        r = self.engine.index_directory(self.directory,
                                        progress_callback=self.sig_progress.emit)
        self.sig_done.emit(r)
