"""
MashupID - Design System & Styles
Premium dark theme with glassmorphism and vibrant accents.
"""

import platform

_OS = platform.system()

# ── Color Palette ─────────────────────────────────────────────────────────────
C_BG       = "#050505"      # Ultra dark background
C_SURFACE  = "#0a0a0a"      # Surface color (cards)
C_SURFACE2 = "#141414"      # Secondary surface (inputs, hover)
C_BORDER   = "rgba(255, 255, 255, 0.08)"
C_ACCENT   = "#00E5FF"      # Cyan Neon (Main action)
C_ACCENT2  = "#FF5252"  # Vibrant Red
C_ACCENT3  = "#FFD740"  # Amber
C_TEXT     = "#EEEEEE"      # Primary text
C_MUTED    = "#8899A6"
C_SUCCESS  = "#69F0AE"  # Mint Green
C_GLASS    = "rgba(25, 25, 35, 0.7)"
C_GRAD     = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1F1F2E, stop:1 #12121A)"

# ── Typography ────────────────────────────────────────────────────────────────
FONT_FAMILY = "Segoe UI" if _OS == 'Windows' else ("SF Pro Display" if _OS == 'Darwin' else "Inter")
BASE_SIZE   = 12 if _OS == 'Windows' else 14 # Slightly larger for 7-inch touch

# ── Global Stylesheet ─────────────────────────────────────────────────────────
GLOBAL_STYLE = f"""
QMainWindow, QWidget {{
    background-color: {C_BG};
    color: {C_TEXT};
    font-family: "{FONT_FAMILY}";
    font-size: {BASE_SIZE}pt;
}}

/* Glass Effect Card */
#Card {{
    background-color: {C_GLASS};
    border: 1px solid {C_BORDER};
    border-radius: 16px;
}}

/* ── Bottom Navigation Bar ── */
#BottomNav {{
    background: {C_SURFACE};
    border-top: 1px solid {C_BORDER};
}}

/* ── Scrollbars ── */
QScrollBar:vertical {{
    background: {C_BG}; width: 8px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #333; border-radius: 4px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: #444; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* ── Tooltips ── */
QToolTip {{
    background: {C_SURFACE2}; color: {C_TEXT};
    border: 1px solid {C_BORDER}; padding: 4px 8px;
    font-size: {BASE_SIZE-1}pt;
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {C_SURFACE};
    border: 1px solid {C_BORDER};
    border-radius: 12px;
    padding: 10px 16px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: rgba(255, 255, 255, 0.05);
    border-color: {C_ACCENT};
}}
QPushButton:pressed {{
    background-color: {C_ACCENT};
    color: #000;
}}
QPushButton:disabled {{
    color: #444; border-color: #111;
}}

/* ── Inputs & Dropdowns ── */
QLineEdit, QComboBox {{
    background: {C_SURFACE}; 
    border: 1px solid {C_BORDER};
    border-radius: 8px; 
    padding: 10px; 
    selection-background-color: {C_ACCENT};
    selection-color: #000;
}}
QLineEdit:focus, QComboBox:focus {{
    border: 1px solid {C_ACCENT};
}}

/* Explicit styling for the dropdown list */
QComboBox QAbstractItemView {{
    background-color: {C_SURFACE2};
    border: 1px solid {C_BORDER};
    selection-background-color: {C_ACCENT};
    selection-color: #000;
    outline: none;
    color: {C_TEXT};
}}
QComboBox QAbstractItemView::item:selected {{
    background-color: {C_ACCENT};
    color: #000;
}}
QComboBox::drop-down {{
    border: none;
    width: 30px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid {C_MUTED};
    margin-right: 10px;
}}

/* ── Progress Bar ── */
QProgressBar {{
    background: {C_SURFACE2}; border: none; border-radius: 6px;
    text-align: center; color: transparent;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {C_ACCENT}, stop:1 {C_ACCENT3});
    border-radius: 6px;
}}

/* ── Table ── */
QTableWidget {{
    background: {C_SURFACE}; gridline-color: {C_BORDER}; border: none;
}}
QHeaderView::section {{
    background: {C_BG}; padding: 8px; border: none;
    font-weight: bold; color: {C_MUTED};
    border-bottom: 1px solid {C_BORDER};
}}
QTableWidget::item {{
    padding: 10px;
}}
QTableWidget::item:selected {{
    background: rgba(0, 229, 255, 0.1); color: {C_ACCENT};
}}
"""
