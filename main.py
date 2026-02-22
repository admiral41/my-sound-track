"""
MashupID - Main Application Entry Point
Premium PyQt6 GUI for Song Identification.
"""

import sys
import os
import platform

# Ensure we can import from core and ui
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QStackedWidget, QLabel, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QPalette, QColor

from core.engine import MashupIDEngine
from ui.styles import C_BG, C_SURFACE, C_ACCENT, C_TEXT, GLOBAL_STYLE, C_BORDER
from ui.widgets import NavBtn, SplashScreen, BrandedHeader, HelpOverlay
from ui.pages import IdentifyPage, ResultsPage, LibraryPage, AddSongsPage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize Engine
        self.engine = MashupIDEngine()
        
        self.setWindowTitle("MashupID")
        self.resize(480, 800)
        self.setMinimumSize(360, 600)
        
        self.setStyleSheet(GLOBAL_STYLE)
        
        self._build_ui()
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_stats)
        self._timer.start(5000)

    def _build_ui(self):
        # Main Stacking (Splash vs Main App)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        
        # 1. Splash Screen
        self.splash = SplashScreen()
        self.splash.finished.connect(self._show_main_app)
        self.stack.addWidget(self.splash)
        
        # 2. Main App Container
        self.main_app_widget = QWidget()
        self.app_layout = QVBoxLayout(self.main_app_widget)
        self.app_layout.setContentsMargins(0, 0, 0, 0)
        self.app_layout.setSpacing(0)
        
        # Header
        self.header = BrandedHeader()
        self.header.help_btn.clicked.connect(self._toggle_help)
        self.app_layout.addWidget(self.header)
        
        # Content
        self.pages_stack = QStackedWidget()
        self.app_layout.addWidget(self.pages_stack)
        
        # Bottom Nav
        self.nav_bar = QWidget()
        self.nav_bar.setObjectName("BottomNav")
        self.nav_bar.setFixedHeight(70)
        nav_lay = QHBoxLayout(self.nav_bar)
        nav_lay.setContentsMargins(10, 0, 10, 0)
        
        self.nav_items = []
        config = [("🔍", "Identify"), ("📊", "Results"), ("📚", "Library"), ("➕", "Add")]
        
        for i, (ico, lbl) in enumerate(config):
            btn = NavBtn(ico, lbl)
            btn.clicked.connect(lambda _, x=i: self._switch_page(x))
            nav_lay.addWidget(btn)
            self.nav_items.append(btn)
            
        self.app_layout.addWidget(self.nav_bar)
        self.stack.addWidget(self.main_app_widget)
        
        # 3. Help Overlay (Global)
        self.help_overlay = HelpOverlay(self)
        
        # Initialize Pages
        self.p_identify = IdentifyPage(self.engine)
        self.p_results  = ResultsPage(self.engine)
        self.p_library  = LibraryPage(self.engine)
        self.p_add      = AddSongsPage(self.engine)
        
        self.pages_stack.addWidget(self.p_identify)
        self.pages_stack.addWidget(self.p_results)
        self.pages_stack.addWidget(self.p_library)
        self.pages_stack.addWidget(self.p_add)
        
        self.p_identify.sig_identified.connect(self._on_identified)
        
        # Default State
        self._switch_page(0)
        self.stack.setCurrentIndex(0) # Show splash first

    def _show_main_app(self):
        self.stack.setCurrentIndex(1)
        
    def _toggle_help(self):
        if self.help_overlay.isHidden():
            self.help_overlay.show()
            self.help_overlay.raise_()
        else:
            self.help_overlay.hide()

    def _switch_page(self, idx):
        self.pages_stack.setCurrentIndex(idx)
        for i, b in enumerate(self.nav_items):
            b.setChecked(i == idx)
        
        if idx == 2: # Library
            self.p_library.refresh()

    def _on_identified(self, result):
        self.p_results.show_result(result)
        self._switch_page(1)

    def _refresh_stats(self):
        # We can update some global stats here if needed, 
        # or leave it for specific pages to handle.
        pass

def main():
    # Handle High DPI on Windows
    if platform.system() == 'Windows':
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except: pass

    app = QApplication(sys.argv)
    app.setApplicationName("MashupID")
    app.setStyle("Fusion")
    
    # Dark Theme Palette (Fallback for widgets ignoring stylesheet)
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(C_BG))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(C_TEXT))
    app.setPalette(pal)

    win = MainWindow()
    win.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
