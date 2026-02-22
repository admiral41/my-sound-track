"""
MashupID - Application Pages
"""

import os
import threading
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QComboBox, QSlider, QFileDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox,
    QLineEdit, QFormLayout, QProgressBar, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QColor

from .styles import *
from .widgets import Card, Gauge, WaveformWidget, RecordBtn, NavBtn
from .workers import IdentifyWorker, SingleIndexWorker, BatchIndexWorker
# Check if we can import engine directly or need relative import
# Assuming this runs from main.py, it's fine.
# But for type hinting:
from core.engine import MashupIDEngine

# ── Identify Page ─────────────────────────────────────────────────────────────
class IdentifyPage(QWidget):
    sig_identified = pyqtSignal(dict)

    def __init__(self, engine: MashupIDEngine, parent=None):
        super().__init__(parent)
        self.engine  = engine
        self._worker = None
        self._tsec   = 0
        self._ttimer = QTimer(self)
        self._ttimer.timeout.connect(self._tick_timer)
        self.setAcceptDrops(True)
        self._build()

    def _build(self):
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(16, 20, 16, 16)
        lay.setSpacing(15)

        self._sub = QLabel("LISTENING MODE")
        self._sub.setStyleSheet(f"color: {C_ACCENT}; font-size: 8pt; font-weight: bold; letter-spacing: 2px;")
        lay.addWidget(self._sub, 0, Qt.AlignCenter)

        # Controls Card
        cc = Card()
        cc.main_layout.setSpacing(12) # Use card's layout directly
        
        # Mode Selector
        mv = QVBoxLayout()
        mv.addWidget(QLabel("ANALYSIS MODE", styleSheet=f"color:{C_MUTED}; font-size:7pt; font-weight:bold;"))
        self._mode = QComboBox()
        self._mode.addItems(["Standard (Single)", "Mashup (Multi)"])
        self._mode.currentIndexChanged.connect(self._on_mode)
        mv.addWidget(self._mode)
        cc.main_layout.addLayout(mv) # Add to card's layout
        
        # Duration Slider
        dv = QVBoxLayout()
        dh = QHBoxLayout()
        dh.addWidget(QLabel("DURATION", styleSheet=f"color:{C_MUTED}; font-size:7pt; font-weight:bold;"))
        dh.addStretch()
        self._dur_lbl = QLabel("10s", styleSheet=f"color:{C_ACCENT}; font-weight:bold; font-size:8pt;")
        dh.addWidget(self._dur_lbl)
        dv.addLayout(dh)
        
        self._dur_sl = QSlider(Qt.Horizontal)
        self._dur_sl.setRange(5, 30); self._dur_sl.setValue(10)
        self._dur_sl.valueChanged.connect(lambda v: self._dur_lbl.setText(f"{v}s"))
        dv.addWidget(self._dur_sl)
        cc.main_layout.addLayout(dv) # Add to card's layout
        
        lay.addWidget(cc)

        # Main Record Area
        rc = Card()
        rc.setMinimumHeight(380) # Slightly taller for better breathing room
        rl = rc.main_layout
        rl.setContentsMargins(15, 20, 15, 20)
        rl.setSpacing(15)
        # Removed alignment to prevent squashing

        # Waveform
        self._wave = WaveformWidget()
        self._wave.setFixedHeight(70)
        rl.addWidget(self._wave)
        rl.addStretch()

        # Button
        self._rbtn = RecordBtn()
        self._rbtn.setFixedSize(110, 110)
        self._rbtn.clicked.connect(self._toggle_rec)
        rl.addWidget(self._rbtn, 0, Qt.AlignCenter)
        
        self._tlbl = QLabel("", styleSheet=f"color:{C_ACCENT}; font-size:18pt; font-weight:bold;")
        self._tlbl.setAlignment(Qt.AlignCenter)
        self._tlbl.hide()
        rl.addWidget(self._tlbl)
        
        rl.addStretch()
        
        fb = QPushButton("📁  Load Audio File")
        fb.setCursor(Qt.PointingHandCursor)
        fb.clicked.connect(self._browse_file)
        rl.addWidget(fb)
        
        self._flbl = QLabel("No file loaded", styleSheet=f"color:{C_MUTED}; font-size:8pt;")
        self._flbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(self._flbl)
        rl.addSpacing(10)
        
        lay.addWidget(rc)

        # Progress Area
        self._pc = Card()
        pl = QHBoxLayout()
        self._pstatus = QLabel("Ready", styleSheet="font-weight:bold; font-size:9pt;")
        self._ppct    = QLabel("0%", styleSheet=f"color:{C_ACCENT}; font-weight:bold; font-size:9pt;")
        pl.addWidget(self._pstatus); pl.addStretch(); pl.addWidget(self._ppct)
        self._pc.main_layout.addLayout(pl)
        
        self._pbar = QProgressBar()
        self._pbar.setRange(0, 100); self._pbar.setValue(0)
        self._pbar.setFixedHeight(4)
        self._pc.main_layout.addWidget(self._pbar)
        lay.addWidget(self._pc)

        lay.addStretch()
        
        scroll.setWidget(container)
        root_lay.addWidget(scroll)

        if not self.engine.has_microphone:
            self._rbtn.setEnabled(False)
            self._sub.setText("No mic detected. Load a file.")

    def _on_mode(self, idx):
        if idx == 1: # Mashup
             if self._dur_sl.value() < 15: self._dur_sl.setValue(15)
             self._sub.setText("Mashup Mode: Analyzes segments to find multiple songs")
        else:
             self._sub.setText("Standard Mode: Identifies a single track")

    def _toggle_rec(self):
        if self._worker and self._worker.isRunning():
            self._worker.stop() # Tell worker to stop waiting
            self.engine.stop()  # Tell engine to stop recording/analyzing
            self._ttimer.stop()
            self._tlbl.hide()
            self._rbtn.set_recording(False)
            self._rbtn.set_analyzing(False)
            self._pstatus.setText("Stopped")
            return
        
        mode = "mashup" if self._mode.currentIndex() == 1 else "standard"
        dur  = self._dur_sl.value()
        
        self._rbtn.set_recording(True)
        self._tsec = dur
        self._tlbl.setText(f"{dur}s")
        self._tlbl.show()
        self._ttimer.start(1000)
        self._wave.set_active(True)
        
        self._start_worker(mode, dur)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Audio", "", "Audio Files (*.wav *.mp3 *.flac *.ogg)")
        if path:
            self._load_file(path)

    def _load_file(self, path):
         if self._worker and self._worker.isRunning(): return
         path = os.path.normpath(path)
         self._flbl.setText(os.path.basename(path))
         self._flbl.setStyleSheet(f"color:{C_ACCENT};")
         
         self._rbtn.set_analyzing(True)
         self._wave.set_active(True)
         
         mode = "mashup" if self._mode.currentIndex() == 1 else "standard"
         self._start_worker(mode, self._dur_sl.value(), path)

    def _start_worker(self, mode, dur, fp=""):
        self._worker = IdentifyWorker(self.engine, mode, dur, fp)
        self._worker.sig_progress.connect(self._on_prog)
        self._worker.sig_status.connect(self._on_status)
        self._worker.sig_level.connect(self._on_level)
        self._worker.sig_result.connect(self._on_result)
        self._worker.start()

    def _tick_timer(self):
        self._tsec -= 1
        if self._tsec <= 0:
            self._ttimer.stop()
            self._tlbl.hide()
            self._tlbl.setText("")
            self._rbtn.set_recording(False)
            self._rbtn.set_analyzing(True)
        else:
            self._tlbl.setText(f"{self._tsec}s")

    def _on_prog(self, p):
        self._pbar.setValue(p)
        self._ppct.setText(f"{p}%")

    def _on_status(self, s, m):
        self._pstatus.setText(m)
        if s in ("done", "error"):
             self._rbtn.set_recording(False); self._rbtn.set_analyzing(False)
             self._wave.set_active(False); self._ttimer.stop(); self._tlbl.hide(); self._tlbl.setText("")

    def _on_level(self, l):
        self._wave.set_level(l); self._wave.push(float(l * 2 - 1))

    def _on_result(self, r):
        self._pbar.setValue(100)
        self._ppct.setText("100%")
        if not r.get('success'):
            self._pstatus.setText(f"FAILED: {r.get('error', 'No matches')}")
            self._pstatus.setStyleSheet(f"color: {C_ACCENT2}; font-weight: bold;")
        else:
            self._pstatus.setText("MATCH FOUND")
            self._pstatus.setStyleSheet(f"color: {C_SUCCESS}; font-weight: bold;")
        self.sig_identified.emit(r)

    # Drag & Drop support
    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls(): e.acceptProposedAction()
    
    def dropEvent(self, e: QDropEvent):
        for url in e.mimeData().urls():
            local = url.toLocalFile()
            if os.path.isfile(local):
                self._load_file(local); break


# ── Results Page ──────────────────────────────────────────────────────────────
class ResultsPage(QWidget):
    def __init__(self, engine: MashupIDEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame) # Clean look
        
        self._container = QWidget()
        self._lay = QVBoxLayout(self._container)
        self._lay.setContentsMargins(24, 24, 24, 24)
        self._lay.setSpacing(16)
        
        scroll.setWidget(self._container)
        QVBoxLayout(self).addWidget(scroll)
        self.layout().setContentsMargins(0,0,0,0)
        self._show_empty()

    def _clear(self):
        while self._lay.count():
            item = self._lay.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def _show_empty(self):
        self._clear()
        
        # Check history when empty
        h = self.engine.db.get_history(limit=5)
        
        l = QLabel("Ready to Identify")
        l.setAlignment(Qt.AlignCenter)
        l.setStyleSheet(f"color:{C_TEXT}; font-size:16pt; font-weight:bold; padding-top:40px;")
        self._lay.addWidget(l)
        
        sub = QLabel("Start listening to see results here.")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"color:{C_MUTED}; font-size:10pt; padding-bottom:20px;")
        self._lay.addWidget(sub)

        if h:
            self._lay.addSpacing(20)
            self._lay.addWidget(QLabel("RECENT HISTORY", styleSheet=f"color:{C_MUTED}; font-size:8pt; font-weight:bold;"))
            for entry in h:
                hc = Card()
                hl = QHBoxLayout()
                dt = entry['timestamp'].split()[1][:5] # HH:MM
                stat = "✅" if entry['success'] else "❌"
                txt = f"{dt}  {stat}  {entry['artist']} - {entry['title']}" if entry['success'] else f"{dt}  {stat}  No Match"
                hl.addWidget(QLabel(txt, styleSheet="font-size:9pt;"))
                hc.main_layout.addLayout(hl)
                self._lay.addWidget(hc)

    def show_result(self, r: dict):
        self._clear()
        
        # Details Info
        v = QVBoxLayout()
        v.setContentsMargins(0, 10, 0, 10)
        
        dur = r.get('total_duration', 0)
        is_mash = r.get('is_mashup', False)
        cnt = r.get('unique_songs', 0)
        
        sub = f"Analysis complete in {r.get('analysis_time',0)}s • {dur:.1f}s audio"
        if is_mash: sub += f"\n{cnt} unique tracks detected"
        v.addWidget(QLabel(sub, styleSheet=f"color:{C_MUTED}; font-size:9pt;"))
        self._lay.addLayout(v)
        
        bh = QHBoxLayout()
        badge = QLabel(" MASHUP " if is_mash else " MATCH ")
        badge.setStyleSheet(f"background:{C_ACCENT3 if is_mash else C_ACCENT}; color:#000; font-size:8pt; font-weight:bold; padding:2px 8px; border-radius:4px;")
        bh.addWidget(badge)
        bh.addStretch()
        self._lay.addLayout(bh)
        
        self._lay.addSpacing(10)

        # Matches
        matches = r.get('matches', [])
        if not r.get('success') or not matches:
             err = Card()
             err.main_layout.addWidget(QLabel("No matches found", styleSheet=f"color:{C_ACCENT2}; font-size:14pt; font-weight:bold;"))
             err.main_layout.addWidget(QLabel("Try a longer duration or check if the song is indexed.", styleSheet=f"color:{C_MUTED};"))
             self._lay.addWidget(err)
        else:
             for i, m in enumerate(matches):
                 self._add_match_card(m, i+1)

        self._lay.addStretch()

    def _add_match_card(self, m, rank):
        c = Card()
        row = QHBoxLayout()
        row.setSpacing(10)
        
        # Rank / Confidence Ring
        rval = m['confidence']
        # Smaller ring for mobile
        gauge = Gauge(C_ACCENT if rval > 70 else (C_ACCENT3 if rval > 40 else C_ACCENT2))
        gauge.setFixedSize(45, 45)
        gauge.set_value(rval / 100.0)
        row.addWidget(gauge)
        
        # Text Info
        info = QVBoxLayout()
        info.setSpacing(2)
        title = QLabel(m['title'])
        title.setWordWrap(True)
        title.setStyleSheet("font-size:11pt; font-weight:bold;")
        info.addWidget(title)
        
        artist = QLabel(m['artist'] or "Unknown Artist")
        artist.setStyleSheet(f"color:{C_MUTED}; font-size:9pt;")
        info.addWidget(artist)
        
        row.addLayout(info, 1)
        
        # Stats / Mashup Time
        stats = QVBoxLayout()
        stats.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        l_conf = QLabel(f"{int(rval)}%")
        l_conf.setStyleSheet(f"color:{C_ACCENT if rval > 60 else C_MUTED}; font-size:13pt; font-weight:800;")
        l_conf.setAlignment(Qt.AlignRight)
        stats.addWidget(l_conf)

        # Segment Info
        if m.get('is_mashup_component'):
            s = m.get('mashup_segment_start', 0)
            e = m.get('mashup_segment_end', 0)
            if e > 0:
                time_str = f"{int(s//60)}:{int(s%60):02d} - {int(e//60)}:{int(e%60):02d}"
                seg_lbl = QLabel(time_str)
                seg_lbl.setStyleSheet(f"color:{C_ACCENT3}; font-size:8pt; font-weight:bold;")
                seg_lbl.setAlignment(Qt.AlignRight)
                stats.addWidget(seg_lbl)
        
        row.addLayout(stats)
        
        c.main_layout.addLayout(row)
        self._lay.addWidget(c)


# ── Library Page ──────────────────────────────────────────────────────────────
class LibraryPage(QWidget):
    def __init__(self, engine: MashupIDEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._songs = []
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16); lay.setSpacing(12)
        
        h = QHBoxLayout()
        h.addWidget(QLabel("LOCAL LIBRARY", styleSheet=f"color: {C_MUTED}; font-size: 8pt; font-weight: bold; letter-spacing: 2px;"))
        h.addStretch()
        
        # Refresh btn
        rb = QPushButton("↻")
        rb.setFixedWidth(40)
        rb.clicked.connect(self.refresh)
        h.addWidget(rb)
        lay.addLayout(h)
        
        # Search
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  Search...")
        self._search.textChanged.connect(self._filter)
        lay.addWidget(self._search)
        
        # Table
        self._tbl = QTableWidget(0, 3)
        self._tbl.setHorizontalHeaderLabels(["Title", "Artist", "Dur"])
        self._tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self._tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl.verticalHeader().setVisible(False)
        lay.addWidget(self._tbl)
        
        # Footer actions
        f = QHBoxLayout()
        dbtn = QPushButton("Delete Selected")
        dbtn.setStyleSheet(f"background:rgba(255,46,99,0.2); color:{C_ACCENT2}; border:1px solid {C_ACCENT2};")
        dbtn.clicked.connect(self._delete_sel)
        f.addWidget(dbtn)
        f.addStretch()
        lay.addLayout(f)

    def refresh(self):
        self._songs = self.engine.get_all_songs()
        self._render(self._songs)

    def _filter(self, q):
        q = q.lower()
        res = [s for s in self._songs if q in s.title.lower() or q in (s.artist or "").lower()]
        self._render(res)

    def _render(self, songs):
        self._tbl.setRowCount(len(songs))
        for r, s in enumerate(songs):
            dur = f"{int(s.duration//60)}:{int(s.duration%60):02d}"
            
            t_item = QTableWidgetItem(s.title)
            t_item.setData(Qt.ItemDataRole.UserRole, s.song_id)
            
            self._tbl.setItem(r, 0, t_item)
            self._tbl.setItem(r, 1, QTableWidgetItem(s.artist))
            self._tbl.setItem(r, 2, QTableWidgetItem(dur))

    def _delete_sel(self):
        rows = sorted(set(i.row() for i in self._tbl.selectedItems()), reverse=True)
        if not rows: return
        
        ans = QMessageBox.question(self, "Delete", f"Delete {len(rows)} songs?", 
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ans != QMessageBox.StandardButton.Yes: return

        for r in rows:
            item = self._tbl.item(r, 0)
            if item:
                sid = item.data(Qt.ItemDataRole.UserRole)
                if sid is not None:
                     self.engine.delete_song(sid)
        self.refresh()


# ── Add Songs Page ────────────────────────────────────────────────────────────
class AddSongsPage(QWidget):
    def __init__(self, engine: MashupIDEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16); lay.setSpacing(12)
        
        lay.addWidget(QLabel("IMPORT SONGS", styleSheet=f"color: {C_MUTED}; font-size: 8pt; font-weight: bold; letter-spacing: 2px;"))
        
        # Single Song Card
        c1 = Card()
        c1.main_layout.addWidget(QLabel("SINGLE FILE", styleSheet=f"color:{C_MUTED}; font-size:7pt; font-weight:bold;"))
        
        f = QFormLayout()
        f.setContentsMargins(0, 5, 0, 5)
        self._fp = QLineEdit(); self._fp.setReadOnly(True); self._fp.setPlaceholderText("Select audio...")
        browse = QPushButton("...")
        browse.setFixedWidth(40)
        browse.clicked.connect(self._browse_single)
        
        hbox = QHBoxLayout(); hbox.addWidget(self._fp); hbox.addWidget(browse)
        f.addRow("File:", hbox)
        
        self._title = QLineEdit(); self._title.setPlaceholderText("Title")
        self._artist = QLineEdit(); self._artist.setPlaceholderText("Artist")
        f.addRow("Title:", self._title)
        f.addRow("Art:", self._artist)
        
        c1.main_layout.addLayout(f)
        
        btn = QPushButton("Index Single")
        btn.clicked.connect(self._idx_single)
        c1.main_layout.addWidget(btn)
        
        self._p1 = QProgressBar(); self._p1.setValue(0); self._p1.hide()
        self._p1.setFixedHeight(4)
        c1.main_layout.addWidget(self._p1)
        
        lay.addWidget(c1)
        
        # Batch Card
        c2 = Card()
        c2.main_layout.addWidget(QLabel("BATCH FOLDER", styleSheet=f"color:{C_MUTED}; font-size:7pt; font-weight:bold;"))
        
        h2 = QHBoxLayout()
        self._dir = QLineEdit(); self._dir.setReadOnly(True); self._dir.setPlaceholderText("Select folder...")
        b2 = QPushButton("...")
        b2.setFixedWidth(40)
        b2.clicked.connect(self._browse_dir)
        h2.addWidget(self._dir); h2.addWidget(b2)
        c2.main_layout.addLayout(h2)
        
        btn2 = QPushButton("Index Folder")
        btn2.clicked.connect(self._idx_batch)
        c2.main_layout.addWidget(btn2)
        
        self._p2 = QProgressBar(); self._p2.setValue(0); self._p2.hide()
        self._p2.setFixedHeight(4)
        c2.main_layout.addWidget(self._p2)
        
        lay.addWidget(c2)
        lay.addStretch()

    def _browse_single(self):
        p, _ = QFileDialog.getOpenFileName(self, "Select File", "", "Audio Files (*.wav *.mp3 *.flac *.ogg)")
        if p:
            self._fp.setText(p)
            self._title.setText(os.path.splitext(os.path.basename(p))[0])

    def _browse_dir(self):
        p = QFileDialog.getExistingDirectory(self, "Select Folder")
        if p:
            self._dir.setText(p)

    def _idx_single(self):
        fp = self._fp.text()
        if not fp: return
        self._p1.show(); self._p1.setValue(0)
        
        self._w1 = SingleIndexWorker(self.engine, fp, self._title.text(), self._artist.text(), "", "", "")
        self._w1.sig_progress.connect(self._p1.setValue)
        self._w1.sig_done.connect(lambda r: self._done(r, self._p1))
        self._w1.start()

    def _idx_batch(self):
        d = self._dir.text()
        if not d: return
        self._p2.show(); self._p2.setValue(0)
        
        self._w2 = BatchIndexWorker(self.engine, d)
        self._w2.sig_progress.connect(self._p2.setValue)
        self._w2.sig_done.connect(lambda r: self._done(r, self._p2))
        self._w2.start()

    def _done(self, r, pbar):
        pbar.setValue(100)
        if r.get('success'):
             QMessageBox.information(self, "Success", "Indexing complete!")
        else:
             QMessageBox.warning(self, "Report", f"Finished.\nFailed files: {r.get('failed', 0)}")
