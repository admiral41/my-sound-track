"""
MashupID - Custom Reusable Widgets
"""
import os
import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QProgressBar, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRect, QSize, QPoint
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QLinearGradient, QRadialGradient,
    QFont, QIcon, QCursor, QPixmap
)
from .styles import *

# ── Glass Card ────────────────────────────────────────────────────────────────
class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        # Layout
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(16, 16, 16, 16)
        self._lay.setSpacing(10)

    # Expose layout properly without shadowing
    @property
    def main_layout(self):
        return self._lay

# ── Value Gauge ───────────────────────────────────────────────────────────────
class Gauge(QWidget):
    def __init__(self, color=C_ACCENT, parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self.value = 0.0
        self.setFixedSize(60, 60)

    def set_value(self, v):
        self.value = v
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(4,4,-4,-4)
        
        # Background track
        p.setPen(QPen(QColor(30,30,30), 4))
        p.drawEllipse(rect)

        # Value arc
        p.setPen(QPen(self.color, 4, Qt.SolidLine, Qt.RoundCap))
        span = int(self.value * 360 * 16)
        p.drawArc(rect, 90 * 16, -span)
        p.end()

# ── Waveform Widget ───────────────────────────────────────────────────────────
class WaveformWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)
        self.setMinimumWidth(200)
        self._data   = np.zeros(120, dtype=np.float32)
        self._level  = 0.0
        self._active = False
        self._phase  = 0.0
        
        # Animation timer
        self._timer  = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)
        self.setAttribute(Qt.WA_StyledBackground, False)

    def set_active(self, v: bool): self._active = v
    def set_level(self, v: float): self._level  = min(max(v, 0.0), 1.0) # Clamp

    def push(self, v: float):
        self._data = np.roll(self._data, -1)
        self._data[-1] = v
        # Also clamp internal data just in case
        np.clip(self._data, -1.0, 1.0, out=self._data)

    def _tick(self):
        if not self._active:
            self._phase += 0.05
            val = float(np.sin(self._phase) * 0.05 + np.random.randn() * 0.01)
            self.push(val)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        mid  = H / 2
        
        # Background
        p.fillRect(0, 0, W, H, QColor(C_SURFACE))

        n  = len(self._data)
        bw = W / n
        
        # Draw bars
        for i, amp in enumerate(self._data):
            bh = max(2, abs(float(amp)) * mid * 0.9)
            x  = i * bw
            
            # Gradient color based on activity
            if self._active:
                 c1 = QColor(C_ACCENT)
                 c2 = QColor(C_ACCENT3)
                 a  = int(60 + 195 * (i / n))
            else:
                 c1 = QColor(C_MUTED)
                 c2 = QColor(30, 30, 40)
                 a  = int(40 + 60 * (i / n))

            g = QLinearGradient(x, mid - bh, x, mid + bh)
            c1.setAlpha(a)
            c2.setAlpha(a // 2)
            g.setColorAt(0.0, c1) 
            g.setColorAt(1.0, c2)

            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(g))
            
            # Rounded bars
            p.drawRoundedRect(int(x)+1, int(mid - bh), max(1, int(bw)-1), int(bh*2), 2, 2)

        p.end()

# ── Animated Record Button ────────────────────────────────────────────────────
class RecordBtn(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 120)
        self._rec   = False
        self._ana   = False
        self._angle = 0.0
        self._pulse = 0.0
        self._pdir  = 1
        self._hover = False
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16) # ~60 FPS
        self.setCursor(Qt.PointingHandCursor)

    def set_recording(self, v):  self._rec = v
    def set_analyzing(self, v):  self._ana = v

    def _tick(self):
        spd = 4 if self._rec else (8 if self._ana else 0.5)
        self._angle = (self._angle + spd) % 360
        
        self._pulse += 0.04 * self._pdir
        if self._pulse >= 1: self._pdir = -1
        if self._pulse <= 0: self._pdir =  1
        self.update()

    def paintEvent(self, _):
        p  = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        cx, cy = W / 2, H / 2
        ro = W / 2 - 8
        ri = ro - 12

        # 1. Outer Glow rings (pulsing)
        if self._rec or self._ana:
            c_glow = QColor(C_ACCENT2 if self._rec else C_ACCENT3)
            max_r  = 15
            alpha  = int(40 * self._pulse)
            for i in range(3):
                p.setPen(QPen(QColor(c_glow.red(), c_glow.green(), c_glow.blue(), alpha), 2))
                p.setBrush(Qt.NoBrush)
                rad = ro + (i + 1) * 5 + (10 * self._pulse)
                p.drawEllipse(QPoint(int(cx), int(cy)), int(rad), int(rad))

        # 2. Base Track
        p.setPen(QPen(QColor(C_BORDER), 3))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPoint(int(cx), int(cy)), int(ro), int(ro))

        # 3. Rotating Arc
        p.save()
        p.translate(cx, cy)
        p.rotate(self._angle)
        
        c_arc = QColor(C_ACCENT2 if self._rec else (C_ACCENT3 if self._ana else C_ACCENT))
        p.setPen(QPen(c_arc, 4, Qt.SolidLine, Qt.RoundCap))
        
        span = 90
        if self._rec: span = 120
        if self._ana: span = 280
        
        p.drawArc(QRect(int(-ro), int(-ro), int(ro*2), int(ro*2)), 0, span * 16)
        p.restore()

        # 4. Inner Button face
        g = QRadialGradient(cx, cy, ri)
        c_face = QColor(C_ACCENT2 if self._rec else (C_ACCENT3 if self._ana else C_ACCENT))
        
        if self._hover:
            c_face.setAlpha(40)
        else:
            c_face.setAlpha(20)
            
        if self._rec or self._ana:
             c_face.setAlpha(60)

        g.setColorAt(0, c_face)
        g.setColorAt(1, QColor(C_SURFACE))

        p.setPen(QPen(c_arc, 2))
        p.setBrush(QBrush(g))
        p.drawEllipse(QPoint(int(cx), int(cy)), int(ri), int(ri))

        # 5. Icon/Text
        icon_txt = "🎙"
        status_txt = "TAP TO LISTEN"
        
        if self._rec:
            icon_txt = "⬛"
            status_txt = "LISTENING..."
        elif self._ana:
            icon_txt = "⚡"
            status_txt = "ANALYZING..."

        f_icon = QFont(FONT_FAMILY, 22)
        p.setFont(f_icon)
        p.setPen(c_arc)
        # Bounding box cy-32 to cy-2 (30px high)
        p.drawText(QRect(0, int(cy - 32), int(W), 30), Qt.AlignCenter, icon_txt)

        f_status = QFont(FONT_FAMILY, 5)
        f_status.setBold(True)
        f_status.setLetterSpacing(QFont.AbsoluteSpacing, 1.0)
        p.setFont(f_status)
        p.setPen(QColor(C_MUTED))
        # Bounding box cy+8 to cy+23 (15px high) to clear the icon and lower arc
        p.drawText(QRect(0, int(cy + 8), int(W), 15), Qt.AlignCenter, status_txt)

        p.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()
    
    def enterEvent(self, _): self._hover = True; self.update()
    def leaveEvent(self, _): self._hover = False; self.update()


# ── Navigation Button ─────────────────────────────────────────────────────────
class NavBtn(QPushButton):
    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(60) # Taller for touch
        self.setMinimumWidth(80)
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 8, 4, 8)
        lay.setSpacing(2)
        
        self.icon_lbl = QLabel(icon)
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setStyleSheet("font-size: 16pt; background: transparent; border: none;")
        
        self.txt_lbl = QLabel(label.upper())
        self.txt_lbl.setAlignment(Qt.AlignCenter)
        self.txt_lbl.setStyleSheet(f"font-size: 7pt; font-weight: bold; color: {C_MUTED}; background: transparent; border: none;")
        
        lay.addWidget(self.icon_lbl)
        lay.addWidget(self.txt_lbl)

        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background: {C_SURFACE2};
            }}
            QPushButton:checked {{
                background: rgba(0, 229, 255, 0.05);
            }}
        """)

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        color = C_ACCENT if checked else C_MUTED
        self.txt_lbl.setStyleSheet(f"font-size: 7pt; font-weight: bold; color: {color}; background: transparent; border: none;")
        self.icon_lbl.setStyleSheet(f"font-size: 16pt; color: {color}; background: transparent; border: none;")


# ── Branded Header ────────────────────────────────────────────────────────────
# Logo
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TopHeader")
        self.setFixedHeight(60)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0)
        
        # Logo
        self.logo = QLabel()
        pix = QPixmap(os.path.join("img", "logo.png"))
        if not pix.isNull():
            self.logo.setPixmap(pix.scaled(120, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.logo.setText("MASHUP ID")
            self.logo.setStyleSheet("font-weight: 800; font-size: 14pt; color: white;")
        
        lay.addWidget(self.logo)
        lay.addStretch()
        
        # Help Button
        self.help_btn = QPushButton("?")
        self.help_btn.setFixedSize(30, 30)
        self.help_btn.setCursor(Qt.PointingHandCursor)
        self.help_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C_SURFACE2};
                border-radius: 15px;
                font-weight: bold;
                color: {C_ACCENT};
                border: 1px solid {C_BORDER};
            }}
            QPushButton:hover {{ background: {C_ACCENT}; color: black; }}
        """)
        lay.addWidget(self.help_btn)

# ── Help Overlay ──────────────────────────────────────────────────────────────
class HelpOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(parent.size() if parent else QSize(480, 800))
        self.setStyleSheet("background: rgba(0,0,0,0.9);")
        self.hide()
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(40, 60, 40, 40)
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(40, 40)
        close_btn.clicked.connect(self.hide)
        close_btn.setStyleSheet("background: transparent; color: white; font-size: 18pt; border: none;")
        lay.addWidget(close_btn, 0, Qt.AlignRight)
        
        title = QLabel("HOW TO USE")
        title.setStyleSheet(f"font-size: 20pt; font-weight: 800; color: {C_ACCENT};")
        lay.addWidget(title)
        
        info = QLabel(
            "1. INDEX YOUR MUSIC\n"
            "   Add your song files in the 'Add Songs' tab.\n\n"
            "2. START LISTENING\n"
            "   Go to 'Identify' and tap the mic icon.\n\n"
            "3. GET RESULTS\n"
            "   The app will detect single tracks or mashups\n"
            "   using spectral analysis optimized for Nano.\n\n"
            "4. VIEW HISTORY\n"
            "   Check past matches in the 'Results' tab."
        )
        info.setWordWrap(True)
        info.setStyleSheet("font-size: 11pt; color: #ccc; line-height: 150%;")
        lay.addWidget(info)
        lay.addStretch()
        
        footer = QLabel("MASHUP ID v2.0 • FOR JETSON NANO")
        footer.setStyleSheet(f"color: {C_MUTED}; font-size: 8pt;")
        footer.setAlignment(Qt.AlignCenter)
        lay.addWidget(footer)

    def showEvent(self, _):
        if self.parent():
            self.resize(self.parent().size())

# ── Splash Screen ─────────────────────────────────────────────────────────────
class SplashScreen(QWidget):
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {C_BG};")
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 40, 0, 40)
        lay.setAlignment(Qt.AlignCenter)
        
        # Initial stretch to push everything towards center/bottom
        lay.addStretch(2)
        
        # 1. Main App Logo (Dead Center)
        self.main_logo = QLabel()
        pix_app = QPixmap(os.path.join("img", "logo.png"))
        if not pix_app.isNull():
            self.main_logo.setPixmap(pix_app.scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        lay.addWidget(self.main_logo, 0, Qt.AlignCenter)
        
        lay.addSpacing(20)
        
        # 2. Status & Progress (Grouped with logo)
        self.title = QLabel("POWERING UP")
        self.title.setStyleSheet(f"font-size: 10pt; font-weight: bold; letter-spacing: 4px; color: {C_MUTED};")
        lay.addWidget(self.title, 0, Qt.AlignCenter)
        
        lay.addSpacing(15)
        
        self.pbar = QProgressBar()
        self.pbar.setFixedSize(220, 4)
        self.pbar.setTextVisible(False)
        self.pbar.setStyleSheet(f"""
            QProgressBar {{ background: {C_SURFACE2}; border: none; border-radius: 2px; }}
            QProgressBar::chunk {{ background: {C_ACCENT}; border-radius: 2px; }}
        """)
        lay.addWidget(self.pbar, 0, Qt.AlignCenter)
        
        # Main stretch to push branding to bottom
        lay.addStretch(3)
        
        # 3. Footer Branding (Bottom)
        fv = QVBoxLayout()
        powered_by = QLabel("POWERED BY")
        powered_by.setStyleSheet(f"color: {C_MUTED}; font-size: 7pt; font-weight: bold; letter-spacing: 2px;")
        powered_by.setAlignment(Qt.AlignCenter)
        fv.addWidget(powered_by)
        
        self.ku_logo = QLabel()
        pix_ku = QPixmap(os.path.join("img", "KU-Logo-Color.png"))
        if not pix_ku.isNull():
            self.ku_logo.setPixmap(pix_ku.scaled(130, 45, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        fv.addWidget(self.ku_logo, 0, Qt.AlignCenter)
        
        lay.addLayout(fv)
        
        # Timer for splash
        self._val = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(30)

    def _step(self):
        self._val += 2
        self.pbar.setValue(self._val)
        if self._val >= 100:
            self._timer.stop()
            self.finished.emit()
