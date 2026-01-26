
import sys
import os
import fitz
import threading
import ctypes
import winreg
from ctypes import wintypes
from concurrent.futures import ThreadPoolExecutor
from PyQt6.QtCore import (
    Qt, QSize, QPropertyAnimation, QEasingCurve, QTimer, pyqtSignal, pyqtProperty, 
    QRect, QRectF, QParallelAnimationGroup, QAbstractAnimation, QEvent
)
from PyQt6.QtGui import QPixmap, QFont, QColor, QImage, QPainter, QBrush, QPen
from PyQt6.QtWidgets import QWidget, QPushButton, QFrame, QApplication, QScrollArea, QVBoxLayout, QHBoxLayout, QLabel, QDialog

# ==========================================
# PROFILES
# ==========================================
PROFILES = {
    "Gestion Humana": {
        "CATEGORIES": [
            ("CC", "Cédula"), ("RQ", "Requisición"), ("HVI", "Hoja de vida interna"), 
            ("CTO", "Contrato laboral"), ("CTOF", "Contrato Firmado"), ("PRE", "Preaviso (Fijo)"), ("EXS", "Otro si (EXS)"),
            ("ARL", "ARL"), ("FEPS", "Formulario EPS"), ("EPS", "EPS"), ("AFP", "AFP"),
            ("FCCF", "Formulario CCF"), ("CCF", "CCF"), ("ADRES", "ADRES"), ("RUAF", "RUAF"),
            ("RC", "Registro Civil"), ("DOCB", "Documentos Beneficiarios"), ("NOIB", "No inclusión"),
            ("HVE", "Hoja de vida externa"), ("EI", "Entrevista"), ("PSI", "Psicotécnicas"),
            ("PC", "Perfil de cargo"), ("AUT", "Autorización datos"), ("ANT", "Antecedentes"), 
            ("CV", "Carnet vacunas"), ("RT", "Registro retefuente"), ("CB", "C. Bancario"), ("LC", "Licencia"),
            ("CL", "Certificados Laborales"), ("CE", "Certificados Estudios"), ("GEO", "GeoVictoria"), ("PO", "Póliza"),
            ("APL", "Aceptación laboral"), ("DOC", "Documentos Adicionales")
        ],
        "SEGMENTS": {
            "A. Contrato y afiliaciones": ["CC", "RQ", "HVI", "CTO", "CTOF", "PRE", "EXS", "ARL", "FEPS", "EPS", "AFP", "FCCF", "CCF", "ADRES", "RUAF", "RC", "DOCB", "NOIB"],
            "B. Documentos de ingreso": ["HVE", "EI", "PSI", "PC", "AUT", "ANT", "CV", "RT", "CB", "LC"],
            "C. Certificaciones": ["CL", "CE"],
            "D. Comunicaciones": ["GEO", "PO", "APL"],
            "E. Documentos Adicionales": ["DOC"]
        }
    },
    "Simplificado": {
        "CATEGORIES": [
            ("CC", "Cédula"), ("CTO", "Contrato"), ("CTOF", "Contrato Firmado"), ("HVI", "Hoja de Vida"), ("EXT", "Otros")
        ],
        "SEGMENTS": {
            "Principales": ["CC", "CTO", "CTOF", "HVI"],
            "Anexos": ["EXT"]
        }
    }
}
DEFAULT_PROFILE = "Gestion Humana"

# ==========================================
# THEMES & STYLING
# ==========================================

THEMES = {
    "light": {
        "bg": "#F8F9FA", "surface": "#FFFFFF", "surface_alt": "#F1F3F5",
        "primary": "#4F46E5", "primary_hover": "#4338CA",
        "secondary": "#EC4899", "accent": "#F59E0B", "success": "#10B981",
        "text": "#1F2937", "text_secondary": "#6B7280", "border": "#E5E7EB",
        "gradient_start": "#4F46E5", "gradient_end": "#7C3AED",
        "selected_bg": "#EEF2FF"
    },
    "dark": {
        "bg": "#0F172A", "surface": "#1E293B", "surface_alt": "#334155",
        "primary": "#818CF8", "primary_hover": "#A5B4FC",
        "secondary": "#F472B6", "accent": "#FBBF24", "success": "#34D399",
        "text": "#F1F5F9", "text_secondary": "#94A3B8", "border": "#475569",
        "gradient_start": "#818CF8", "gradient_end": "#C084FC",
        "selected_bg": "#312E81"
    }
}

class ThemeManager:
    """Manages global application theme state"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ThemeManager, cls).__new__(cls)
            cls._instance.theme_mode = "dark"
            cls._instance.transparency_mode = "mica"
            cls._instance.auto_theme = False
            cls._instance.transparency_level = 160
        return cls._instance

    def get_theme(self):
        current_mode = self.theme_mode
        if self.auto_theme:
            is_dark = is_system_dark_mode()
            current_mode = "dark" if is_dark else "light"
        
        t = THEMES[current_mode].copy()
        
        # Inject system accent if auto
        if self.auto_theme:
            accent = get_system_accent_color()
            t["primary"] = accent
            t["primary_hover"] = adjust_color_brightness(accent, 1.2 if current_mode == "dark" else 0.8)
            t["gradient_start"] = accent
            t["gradient_end"] = adjust_color_brightness(accent, 1.4 if current_mode == "dark" else 0.6)
        
        return t

    def get_stylesheet(self):
        t = self.get_theme()
        is_dark = self.theme_mode == "dark" or (self.auto_theme and is_system_dark_mode())
        
        if self.transparency_mode == "acrylic":
            widget_opacity = min(255, self.transparency_level + 15)
            border_opacity = min(255, self.transparency_level + 30)
            if is_dark:
                glass_bg = f"rgba(25, 25, 25, {widget_opacity})"
                glass_border = f"rgba(255, 255, 255, {border_opacity//6})"
                sidebar_bg = f"rgba(20, 20, 20, {widget_opacity + 10})"
            else:
                glass_bg = f"rgba(255, 255, 255, {widget_opacity})"
                glass_border = f"rgba(0, 0, 0, {border_opacity//10})"
                sidebar_bg = f"rgba(248, 248, 248, {widget_opacity + 10})"
        else:
            if is_dark:
                glass_bg = "rgba(40, 40, 40, 150)"
                glass_border = "rgba(255, 255, 255, 0.05)"
                sidebar_bg = "rgba(30, 30, 30, 80)"
            else:
                glass_bg = "rgba(255, 255, 255, 150)"
                glass_border = "rgba(0, 0, 0, 0.03)"
                sidebar_bg = "rgba(248, 248, 248, 80)"
                
        return f"""
        QMainWindow, #centralWidget, QStackedWidget {{ background: transparent !important; }}
        QWidget {{ background-color: transparent; color: {t['text']}; font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif; font-size: 14px; }}
        QFrame#categoryPanel {{ background-color: {sidebar_bg}; border-right: 1px solid {glass_border}; border-radius: 0px; }}
        QPushButton#navButton {{ background-color: transparent; color: {t['text_secondary']}; border: none; text-align: left; padding: 0px 16px; margin: 1px 10px; min-height: 40px; border-radius: 4px; font-size: 13px; font-weight: 400; }}
        QPushButton#navButton:hover {{ background-color: rgba(140, 140, 140, 18); }}
        QPushButton#navButton:checked {{ background-color: rgba(120, 120, 120, 25); color: {t['text']}; font-weight: 500; }}
        QPushButton {{ background-color: {glass_bg}; color: {t['text']}; border: 1px solid {glass_border}; padding: 6px 14px; font-size: 13px; font-weight: 500; border-radius: 4px; }}
        QPushButton:hover {{ background-color: rgba(130, 130, 130, 20); border: 1px solid rgba(130, 130, 130, 40); }}
        QPushButton:pressed {{ background-color: rgba(130, 130, 130, 35); }}
        QLineEdit, QComboBox {{ background-color: {glass_bg}; border: 1px solid {glass_border}; border-radius: 4px; padding: 5px 10px; color: {t['text']}; }}
        QLineEdit:focus, QComboBox:focus {{ border-bottom: 2px solid {t['primary']}; background-color: rgba(255, 255, 255, 0.08); }}
        QSlider::groove:horizontal {{ background: rgba(120, 120, 120, 30); height: 3px; border-radius: 1px; }}
        QSlider::handle:horizontal {{ background: {t['primary']}; width: 12px; height: 12px; margin: -5px 0; border-radius: 6px; }}
        QSlider::sub-page:horizontal {{ background: {t['primary']}; border-radius: 1px; }}
        QLabel#title {{ font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif; font-size: 26px; font-weight: 500; color: {t['text']}; letter-spacing: -0.5px; }}
        QLabel#subtitle {{ font-family: 'Segoe UI Variable Small', 'Segoe UI', sans-serif; font-size: 13px; color: {t['text_secondary']}; opacity: 0.8; }}
        QPushButton#primaryButton {{ background-color: {t['primary']}; color: white; border: none; font-weight: 500; border-radius: 4px; padding: 8px 22px; }}
        QPushButton#primaryButton:hover {{ background-color: {t['primary_hover']}; }}
        QPushButton#smallBtn {{ padding: 4px 12px; font-size: 12px; background-color: rgba(120, 120, 120, 15); border: 1px solid rgba(255, 255, 255, 0.05); }}
        QPushButton#smallBtn:hover {{ background-color: rgba(120, 120, 120, 25); }}
        """

# Backwards compatibility helpers
def get_theme():
    return get_theme_manager().get_theme()

def get_stylesheet():
    return get_theme_manager().get_stylesheet()

def is_acrylic_theme():
    return get_theme_manager().transparency_mode == "acrylic"

def is_drawing_glass():
    return True

class ThemeWatcher(threading.Thread):
    def __init__(self, callback):
        super().__init__(daemon=True)
        self.callback = callback
        self.last_dark_state = is_system_dark_mode()
        self.last_accent = get_system_accent_color()
        self._stop_event = threading.Event()
    def run(self):
        while not self._stop_event.is_set():
            current_dark = is_system_dark_mode()
            current_accent = get_system_accent_color()
            if current_dark != self.last_dark_state or current_accent != self.last_accent:
                self.last_dark_state = current_dark
                self.last_accent = current_accent
                self.callback(current_dark)
            self._stop_event.wait(2)
    def stop(self): self._stop_event.set()

# Helper to access singleton easily
def get_theme_manager():
    return ThemeManager()

# ==========================================
# WINDOWS EFFECT (DWM)
# ==========================================
class WindowsEffect:
    """Windows DWM API for blur/transparency effects - Compatible with Win10/11"""
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    DWMWA_SYSTEMBACKDROP_TYPE = 38
    ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
    
    _dwmapi = None
    _dwm_set_attr = None
    _dwm_extend = None

    @staticmethod
    def _init_dwm():
        if WindowsEffect._dwmapi is None:
            try:
                WindowsEffect._dwmapi = ctypes.windll.dwmapi
                WindowsEffect._dwm_set_attr = WindowsEffect._dwmapi.DwmSetWindowAttribute
                WindowsEffect._dwm_extend = WindowsEffect._dwmapi.DwmExtendFrameIntoClientArea
            except: pass

    @staticmethod
    def set_window_dark_mode(hwnd, dark=True):
        WindowsEffect._init_dwm()
        if not WindowsEffect._dwm_set_attr: return False
        try:
            value = ctypes.c_int(1 if dark else 0)
            WindowsEffect._dwm_set_attr(hwnd, WindowsEffect.DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))
            return True
        except:
            return False
            
    @staticmethod
    def apply_best_effect(hwnd, dark_mode=False, alpha=160, use_acrylic=False):
        WindowsEffect._init_dwm()
        if not WindowsEffect._dwm_extend: return False
        try:
            # Extend frame (Mandatory)
            margins = (-1, -1, -1, -1)
            margin_struct = type('MARGINS', (ctypes.Structure,), {'_fields_': [('cxLeftWidth', ctypes.c_int), ('cxRightWidth', ctypes.c_int), ('cyTopHeight', ctypes.c_int), ('cyBottomHeight', ctypes.c_int)]})(*margins)
            WindowsEffect._dwm_extend(hwnd, ctypes.byref(margin_struct))
            
            if dark_mode: WindowsEffect.set_window_dark_mode(hwnd, True)
            
            # Win 11 Backdrop
            if WindowsEffect._dwm_set_attr:
                val = 3 if use_acrylic else 2
                ctype_val = ctypes.c_int(val)
                res = WindowsEffect._dwm_set_attr(hwnd, WindowsEffect.DWMWA_SYSTEMBACKDROP_TYPE, ctypes.byref(ctype_val), ctypes.sizeof(ctype_val))
                if res == 0: return True
        except:
            pass
        return False

# ==========================================
# SYSTEM HELPERS
# ==========================================
def is_system_dark_mode():
    try:
        registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except:
        return False

def get_system_accent_color():
    try:
        registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\DWM")
        value, _ = winreg.QueryValueEx(key, "AccentColor")
        b = (value >> 16) & 0xFF
        g = (value >> 8) & 0xFF
        r = value & 0xFF
        return f"#{r:02x}{g:02x}{b:02x}"
    except:
        return "#0078D4"
        
def adjust_color_brightness(hex_color, factor):
    hex_color = hex_color.lstrip('#')
    try:
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = min(255, max(0, int(r * factor)))
        g = min(255, max(0, int(g * factor)))
        b = min(255, max(0, int(b * factor)))
        return f"#{r:02x}{g:02x}{b:02x}"
    except:
        return hex_color

class AnimatedButton(QPushButton):
    """High-performance minimalist animated button"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._glow_opacity = 0.0
        self.fade_anim = QPropertyAnimation(self, b"glowColorOpacity")
        self.fade_anim.setDuration(200)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
    @pyqtProperty(float)
    def glowColorOpacity(self):
        return self._glow_opacity
    @glowColorOpacity.setter
    def glowColorOpacity(self, value):
        self._glow_opacity = value
        self.update()
        
    def paintEvent(self, event):
        super().paintEvent(event)
        if self._glow_opacity > 0.01:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            tm = get_theme_manager()
            color = QColor(tm.get_theme()['primary'])
            color.setAlphaF(self._glow_opacity * 0.25)
            painter.setBrush(color)
            border_color = QColor(tm.get_theme()['primary'])
            border_color.setAlphaF(self._glow_opacity * 0.4)
            painter.setPen(border_color)
            rect = self.rect().adjusted(1, 1, -1, -1)
            painter.drawRoundedRect(rect, 4, 4)

    def enterEvent(self, event):
        super().enterEvent(event)
        self.fade_anim.stop()
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.start()
    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.fade_anim.stop()
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.start()

class AutoDrawer(QFrame):
    """Base class for robust auto-hiding drawers"""
    expanded = pyqtSignal()
    collapsed = pyqtSignal()
    
    def __init__(self, parent=None, expanded_size=280, collapsed_size=10, vertical=False):
        super().__init__(parent)
        self.expanded_size = expanded_size
        self.collapsed_size = collapsed_size
        self.vertical = vertical
        self.is_expanded = False
        
        self.open_timer = QTimer(self)
        self.open_timer.setSingleShot(True)
        self.open_timer.setInterval(200)
        self.open_timer.timeout.connect(self._check_and_open)
        
        self.close_timer = QTimer(self)
        self.close_timer.setSingleShot(True)
        self.close_timer.setInterval(300)
        self.close_timer.timeout.connect(self._check_and_close)
        
        prop = b"maximumHeight" if vertical else b"minimumWidth"
        self.anim = QPropertyAnimation(self, prop)
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.finished.connect(self._on_anim_finished)
        self.anim.valueChanged.connect(self._on_anim_value)
        
        self.content_widget = QWidget()
        if vertical: self.content_layout = QHBoxLayout(self.content_widget)
        else: self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(10)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0,0,0,0)
        self.main_layout.addWidget(self.content_widget)
        self.content_widget.hide()
        
        if vertical: self.setFixedHeight(collapsed_size)
        else: self.setFixedWidth(collapsed_size)

    def addWidget(self, widget):
        self.content_layout.addWidget(widget)
        
    def addStretch(self):
        self.content_layout.addStretch()

    def set_expanded_size(self, size):
        self.expanded_size = size
        # If currently expanded, update animation/size immediately?
        # For safety, let's just update the target variable. 
        # If open, the next toggle will use it, or we could force update.
        if self.is_expanded:
            if self.vertical: self.setFixedHeight(size)
            else: self.setFixedWidth(size)
            self.anim.setStartValue(size) # Update anim start check?
            # Actually, _start_anim sets values. 
            pass

    def enterEvent(self, event):
        super().enterEvent(event)
        self.close_timer.stop()
        if not self.is_expanded and self.anim.state() != QAbstractAnimation.State.Running:
            self.open_timer.start()
    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.open_timer.stop()
        if self.is_expanded and self.anim.state() != QAbstractAnimation.State.Running:
             self.close_timer.start()
    def _check_and_open(self):
        if self.underMouse(): self._start_anim(True)
    def _check_and_close(self):
        pos = self.mapFromGlobal(self.cursor().pos())
        if not self.rect().contains(pos): self._start_anim(False)
    def _start_anim(self, expand):
        self.is_expanded = expand
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        start = self.collapsed_size if expand else self.expanded_size
        end = self.expanded_size if expand else self.collapsed_size
        if expand: self.content_widget.show()
        self.anim.stop()
        self.anim.setStartValue(start)
        self.anim.setEndValue(end)
        self.anim.start()
    def _on_anim_finished(self):
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        if not self.is_expanded: 
            self.content_widget.hide()
            self.collapsed.emit()
        else:
            self.expanded.emit()
            
        pos = self.mapFromGlobal(self.cursor().pos())
        is_inside = self.rect().contains(pos)
        if self.is_expanded and not is_inside: self.close_timer.start()
        elif not self.is_expanded and is_inside: self.open_timer.start()
    def _on_anim_value(self, value):
        if self.vertical: self.setFixedHeight(value)
        else: self.setFixedWidth(value)

class PDFEngine:
    _executor = ThreadPoolExecutor(max_workers=os.cpu_count())

    def __init__(self, file_path):
        self.file_path = file_path
        self.doc = fitz.open(file_path)
        self.cache = {}
        self.cache_keys = []
        self.max_cache_size = 50
        self.rotations = {}
        self._lock = threading.Lock()

    def get_page_preview(self, page_num, scale=0.3, prefetch=True):
        rot = self.rotations.get(page_num, 0)
        key = (page_num, scale, rot)
        with self._lock:
            if key in self.cache: 
                # Predictive load next page
                if prefetch and page_num + 1 < self.doc.page_count:
                    self._executor.submit(self.get_page_preview, page_num + 1, scale, False)
                return self.cache[key]
        try:
            page = self.doc.load_page(page_num)
            matrix = fitz.Matrix(scale, scale).prerotate(rot)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(img)
            with self._lock:
                if len(self.cache_keys) >= self.max_cache_size:
                    old_key = self.cache_keys.pop(0)
                    if old_key in self.cache: del self.cache[old_key]
                self.cache[key] = pixmap
                self.cache_keys.append(key)
            
            # Predictive load next page if this was a direct request
            if prefetch and page_num + 1 < self.doc.page_count:
                self._executor.submit(self.get_page_preview, page_num + 1, scale, False)
                
            return pixmap
        except: return None

    def rotate_page(self, page_num):
        curr = self.rotations.get(page_num, 0)
        self.rotations[page_num] = (curr + 90) % 360
        with self._lock:
            for k in [k for k in self.cache if k[0] == page_num]:
                del self.cache[k]
    def close(self):
        self.doc.close()

# ==========================================
# DIALOGS
# ==========================================

class FullPageDialog(QDialog):
    def __init__(self, engine, page_num, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Vista Completa - Página {page_num + 1}")
        self.resize(800, 900)
        # Use Mica if available
        try:
             WindowsEffect.apply_best_effect(int(self.winId()), dark_mode=is_system_dark_mode())
        except: pass
        
        layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        img_lbl = QLabel()
        img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_lbl.setStyleSheet("background-color: transparent;")
        
        # High Res Preview
        pix = engine.get_page_preview(page_num, scale=2.0)
        if pix:
            img_lbl.setPixmap(pix)
            
        scroll.setWidget(img_lbl)
        layout.addWidget(scroll)
        
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
# ==========================================
# FILE OPERATIONS
# ==========================================
def merge_pdfs(paths):
    """Merge multiple PDFs into one temporary file"""
    if not paths: return None
    if len(paths) == 1: return paths[0]
    
    try:
        merged_doc = fitz.open()
        for path in paths:
            with fitz.open(path) as doc:
                merged_doc.insert_pdf(doc)
        
        # Save to temp
        import tempfile, time
        temp_dir = tempfile.gettempdir()
        name = f"merged_{int(time.time())}.pdf"
        out_path = os.path.join(temp_dir, name)
        
        merged_doc.save(out_path)
        merged_doc.close()
        return out_path
    except Exception as e:
        print(f"Merge error: {e}")
        return None
