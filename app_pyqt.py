"""
ITMQ-GD v2.0.0 (dev) - PyQt6
Full-featured editor with all requested functionality
With Windows Aero Glass Effect
"""
import sys
import os
import json
import fitz
import unicodedata
import threading
import re
import ctypes
import itmq_license
from ctypes import wintypes
import shutil
import datetime
import winreg
from concurrent.futures import ThreadPoolExecutor
from PyQt6.QtCore import (
    Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve, QUrl, 
    QAbstractAnimation, QParallelAnimationGroup, QEvent, QPoint, QRect,
    pyqtSignal, pyqtProperty, QPointF, QBuffer, QIODevice, QRectF
)
from PyQt6.QtGui import QPixmap, QFont, QColor, QImage, QWheelEvent, QPainter, QBrush, QPen
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QStackedWidget, QFileDialog, 
    QScrollArea, QSizePolicy, QSpacerItem, QGridLayout, QLineEdit, 
    QComboBox, QGraphicsDropShadowEffect, QTabWidget, QSplashScreen,
    QSlider, QDialog, QDialogButtonBox, QMessageBox, QGraphicsBlurEffect,
    QGraphicsOpacityEffect, QTabBar, QGraphicsView, QGraphicsScene, 
    QGraphicsPixmapItem, QGraphicsSimpleTextItem, QScroller, QScrollerProperties,
    QAbstractItemView, QMenu, QTextEdit, QApplication, QInputDialog
)
from PyQt6.QtCore import QPointF

# Import Shared Core
# Import Shared Core
from app_shared import (
    WindowsEffect, get_theme_manager, AnimatedButton, AutoDrawer,
    PDFEngine, PROFILES, DEFAULT_PROFILE, get_theme, get_stylesheet,
    adjust_color_brightness, is_system_dark_mode, get_system_accent_color,
    is_drawing_glass, is_acrylic_theme, FullPageDialog, merge_pdfs
)

# OCR Config
# OCR Config
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ML Core
try:
    from ai_core import ModelManager
except ImportError:
    print("Warning: ai_core.py not found. AI features disabled.")
    class ModelManager:
        def __new__(cls): return None # Dummy
        def predict(self, x): return None
        def learn(self, x, y): pass

# ==========================================
# SETTINGS PERSISTENCE
# ==========================================
SETTINGS_FILE = "user_settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    except:
        pass

# ==========================================
# WINDOWS AERO BLUR EFFECT (DWM API)
# ==========================================


# ==========================================
# WINDOWS AERO BLUR EFFECT (DWM API)
# ==========================================
# Moved to app_shared.py


# ==========================================
# SYSTEM THEME DETECTION
# ==========================================

def is_system_dark_mode():
    """Check if Windows is in dark mode by reading registry"""
    try:
        registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except Exception as e:
        print(f"Error reading system theme: {e}")
        return False

def get_system_accent_color():
    """Get Windows system accent color from registry"""
    try:
        registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\DWM")
        value, _ = winreg.QueryValueEx(key, "AccentColor")
        # Format is AABBGGRR
        b = (value >> 16) & 0xFF
        g = (value >> 8) & 0xFF
        r = value & 0xFF
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception as e:
        print(f"Error reading accent color: {e}")
        return "#0078D4" # Default Windows blue

def adjust_color_brightness(hex_color, factor):
    """Adjust color brightness (factor > 1 for lighter, < 1 for darker)"""
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    
    r = min(255, max(0, int(r * factor)))
    g = min(255, max(0, int(g * factor)))
    b = min(255, max(0, int(b * factor)))
    
    return f"#{r:02x}{g:02x}{b:02x}"

class ThemeWatcher(threading.Thread):
    """Thread that watches for system theme and accent color changes"""
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
            self._stop_event.wait(2)  # Check every 2 seconds

    def stop(self):
        self._stop_event.set()

# ==========================================
# ANIMATION HELPERS
# ==========================================

# ==========================================
# ANIMATION HELPERS
# ==========================================
# AnimatedButton is imported from app_shared

# AutoDrawer is imported from app_shared

class SideBar(AutoDrawer):
    """Main App Sidebar (Left)"""
    def __init__(self, parent=None):
        super().__init__(parent, expanded_size=280, collapsed_size=25, vertical=False)
        self.setObjectName("categoryPanel")
        self.content_layout.setContentsMargins(15, 30, 15, 20)

class BottomBar(AutoDrawer):
    """Editor Steps Bar (Bottom)"""
    def __init__(self, parent=None):
        super().__init__(parent, expanded_size=140, collapsed_size=25, vertical=True)
        self.setObjectName("categoryPanel") # Reuse style
        self.content_layout.setContentsMargins(20, 10, 20, 10)

class FadeStackedWidget(QStackedWidget):
    """StackedWidget wrapper, transition effects removed for stability with Acrylic transparency"""
    def __init__(self, parent=None):
        super().__init__(parent)

    def setCurrentIndex(self, index):
        if index == self.currentIndex():
            return
        super().setCurrentIndex(index)

    def setCurrentWidget(self, widget):
        if widget == self.currentWidget():
            return
        super().setCurrentWidget(widget)

# ==========================================
# FULL PAGE PREVIEW DIALOG
# ==========================================

class FullPageDialog(QDialog):
    def __init__(self, engine, page_num, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.page_num = page_num
        self.setWindowTitle(f"Página {page_num + 1}")
        self.setMinimumSize(800, 900)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Image
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll = QScrollArea()
        scroll.setWidget(self.image_label)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        # Buttons
        btn_row = QHBoxLayout()
        rotate_btn = AnimatedButton("↻ Rotar 90°")
        rotate_btn.clicked.connect(self._rotate)
        btn_row.addWidget(rotate_btn)
        
        close_btn = AnimatedButton("Cerrar")
        close_btn.setObjectName("primaryButton")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
        
        self._load_image()
    
    def _load_image(self):
        pixmap = self.engine.get_page_preview(self.page_num, 2.0)  # High res
        if pixmap:
            self.image_label.setPixmap(pixmap)
    
    def _rotate(self):
        self.engine.rotate_page(self.page_num)
        self._load_image()

# ==========================================
# CÉDULA VERIFICATION DIALOG
# ==========================================

class ZoomableScrollArea(QGraphicsView):
    """Interactive GraphicsView with Zoom & Pan support"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene_obj = QGraphicsScene(self)
        self.setScene(self.scene_obj)
        
        # Native Panning
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        # Hide Scrollbars (Pan is enough)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("background-color: transparent;")
        
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene_obj.addItem(self.pixmap_item)
        self.base_pixmap = None

    def set_image(self, pixmap):
        self.base_pixmap = pixmap
        self.pixmap_item.setPixmap(pixmap)
        self.scene_obj.setSceneRect(QRectF(pixmap.rect()))
        self.fitInView(self.scene_obj.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def zoom_in(self):
        self.scale(1.2, 1.2)
        
    def zoom_out(self):
        self.scale(1/1.2, 1/1.2)

    def wheelEvent(self, event):
        # Always zoom interactively
        factor = 1.15
        if event.angleDelta().y() < 0:
            factor = 1.0 / factor
        self.scale(factor, factor)
        event.accept()

class CedulaDialog(QDialog):
    def __init__(self, engine, page_num, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.page_num = page_num
        self.result_data = None
        
        self.setWindowTitle("Verificar Cédula")
        self.resize(1200, 800) # Default large size
        self.showMaximized()   # Maximize immediately
        
        # Main Layout: Split Screen
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # --- LEFT: INTERACTIVE PREVIEW ---
        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(20, 20, 20, 20)
        preview_layout.setSpacing(10)
        
        # Toolbar (Zoom/Rotate)
        toolbar = QHBoxLayout()
        toolbar.addStretch()
        
        z_out = AnimatedButton("−")
        z_out.setFixedSize(32, 32)
        z_out.clicked.connect(lambda: self.preview_area.zoom_out())
        toolbar.addWidget(z_out)
        
        z_reset = AnimatedButton("1:1")
        z_reset.setFixedWidth(50)
        z_reset.clicked.connect(self._reset_zoom)
        toolbar.addWidget(z_reset)
        
        z_in = AnimatedButton("+")
        z_in.setFixedSize(32, 32)
        z_in.clicked.connect(lambda: self.preview_area.zoom_in())
        toolbar.addWidget(z_in)
        
        toolbar.addSpacing(20)
        
        rot_btn = AnimatedButton("↻ Rotar")
        rot_btn.clicked.connect(self._rotate)
        toolbar.addWidget(rot_btn)
        
        toolbar.addStretch()
        preview_layout.addLayout(toolbar)
        
        # Scroll Area
        self.preview_area = ZoomableScrollArea()
        preview_layout.addWidget(self.preview_area)
        
        layout.addWidget(preview_container, stretch=3) # 75% width
        
        # Vertical Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet("color: rgba(128,128,128,0.5);")
        layout.addWidget(line)
        
        # --- RIGHT: FORM ---
        form_container = QFrame()
        form_container.setObjectName("categoryPanel") # Reuse side panel style
        form_container.setFixedWidth(350)
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(30, 40, 30, 40)
        form_layout.setSpacing(15)
        
        form_layout.addWidget(QLabel("Validación de Datos"))
        
        # Form Fields
        form_layout.addWidget(QLabel("Apellidos:"))
        self.apellido_input = QLineEdit()
        self.apellido_input.setPlaceholderText("Apellidos")
        form_layout.addWidget(self.apellido_input)
        
        form_layout.addWidget(QLabel("Nombres:"))
        self.nombre_input = QLineEdit()
        self.nombre_input.setPlaceholderText("Nombres")
        form_layout.addWidget(self.nombre_input)
        
        form_layout.addWidget(QLabel("Cédula:"))
        self.cedula_input = QLineEdit()
        self.cedula_input.setPlaceholderText("Número de Cédula")
        form_layout.addWidget(self.cedula_input)
        
        form_layout.addSpacing(20)
        
        # Buttons
        confirm_btn = AnimatedButton("✓ Confirmar Datos")
        confirm_btn.setObjectName("primaryButton")
        confirm_btn.setMinimumHeight(45)
        confirm_btn.clicked.connect(self._confirm)
        form_layout.addWidget(confirm_btn)
        
        cancel_btn = AnimatedButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        form_layout.addWidget(cancel_btn)
        
        form_layout.addStretch()
        layout.addWidget(form_container)
        
        # Navigation
        self.apellido_input.returnPressed.connect(self.nombre_input.setFocus)
        self.nombre_input.returnPressed.connect(self.cedula_input.setFocus)
        self.cedula_input.returnPressed.connect(self._confirm)
        
        # Init
        self._load_preview()

    def _load_preview(self):
        # Fetch high-res preview for zooming
        pixmap = self.engine.get_page_preview(self.page_num, scale=2.0)
        if pixmap:
            self.preview_area.set_image(pixmap)

    def _rotate(self):
        self.engine.rotate_page(self.page_num)
        self._load_preview()
        
    def _reset_zoom(self):
        # Fit to view
        if self.preview_area.scene_obj.items():
             self.preview_area.fitInView(self.preview_area.scene_obj.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _confirm(self):
        apellido = self.apellido_input.text().strip()
        nombre = self.nombre_input.text().strip()
        cedula = self.cedula_input.text().strip()
        
        if not all([apellido, nombre, cedula]):
            QMessageBox.warning(self, "Datos Incompletos", "Por favor complete todos los campos.")
            return
        
        self.result_data = (apellido, nombre, cedula)
        self.accept()

# ==========================================
# PAGE CARD
# ==========================================

class PageCard(QFrame):
    clicked = pyqtSignal(int, Qt.KeyboardModifier) # Updated to send modifiers
    rotate_requested = pyqtSignal(int)
    right_clicked = pyqtSignal(int)
    
    def __init__(self, page_num, parent=None, initial_scale=0.25):
        super().__init__(parent)
        self.page_num = page_num
        self.selected = False
        self.hidden = False
        self.scale = initial_scale
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Hover Glow State
        self._glow_opacity = 0.0
        self.glow_anim = QPropertyAnimation(self, b"glowOpacity")
        self.glow_anim.setDuration(250)
        self.glow_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(False) # We scale manually for quality
        layout.addWidget(self.image_label)
        
        # Call update_zoom AFTER image_label is created
        self.update_zoom(initial_scale)
        
        bottom = QHBoxLayout()
        self.page_label = QLabel(f"Pág {page_num + 1}")
        self.page_label.setStyleSheet("font-weight: 700; font-size: 11px;")
        bottom.addWidget(self.page_label)
        
        rotate_btn = AnimatedButton("↻")
        rotate_btn.setFixedSize(24, 24)
        rotate_btn.setStyleSheet("border-radius: 12px; font-size: 12px; padding: 0;")
        rotate_btn.clicked.connect(lambda: self.rotate_requested.emit(self.page_num))
        bottom.addWidget(rotate_btn)
        layout.addLayout(bottom)
        
        self._update_style()
    
    def update_zoom(self, scale):
        self.scale = scale
        # Calculate dynamic size (base size is roughly 600x800 for full page, 0.25 scale = 150x200)
        w = int(640 * scale)
        h = int(840 * scale)
        self.setFixedSize(w, h)
        # Force label to take rest of space
        self.image_label.setMinimumHeight(h - 50)
    
    def set_image(self, pixmap):
        if pixmap:
            # Use fixed targets based on scale for consistency and sharpness
            w = int(600 * self.scale)
            h = int(800 * self.scale)
            
            if pixmap.width() != w or pixmap.height() != h:
                pixmap = pixmap.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            
            self.image_label.setPixmap(pixmap)
    
    def set_selected(self, selected, label_text=None):
        self.selected = selected
        self.page_label.setText(label_text if label_text else f"Pág {self.page_num + 1}")
        self._update_style()
    
    def set_hidden(self, hidden):
        self.hidden = hidden
        self.setVisible(not hidden)
    
    def _update_style(self):
        t = get_theme()
        is_dark = t['bg'].lower() in ["#0f172a", "#1e293b"] # Heuristic for dark mode
        img_bg = "rgba(255, 255, 255, 0.05)" if is_dark else "rgba(0, 0, 0, 0.03)"
        
        self.image_label.setStyleSheet(f"background-color: {img_bg}; border-radius: 10px;")
        
        if self.selected:
            self.setStyleSheet(f"""
                PageCard {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {t['gradient_start']}, stop:1 {t['gradient_end']}); border-radius: 16px; border: 2px solid transparent; }}
                QLabel {{ color: white; }}
            """)
        else:
            self.setStyleSheet(f"PageCard {{ background-color: {t['surface']}; border-radius: 16px; border: 2px solid {t['border']}; }}")
    
    @pyqtProperty(float)
    def glowOpacity(self):
        return self._glow_opacity
    
    @glowOpacity.setter
    def glowOpacity(self, value):
        self._glow_opacity = value
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._glow_opacity > 0.01:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            t = get_theme()
            color = QColor(t['primary'])
            
            # Draw glow border
            pen = QPen(color)
            pen.setWidthF(2.0 + self._glow_opacity * 2.0)
            color.setAlphaF(self._glow_opacity * 0.5)
            painter.setPen(pen)
            
            # Outer glow
            rect = self.rect().adjusted(2, 2, -2, -2)
            painter.drawRoundedRect(rect, 16, 16)
            
            # Subtle fill glow if not selected
            if not self.selected:
                color.setAlphaF(self._glow_opacity * 0.1)
                painter.setBrush(color)
                painter.drawRoundedRect(rect, 16, 16)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit(self.page_num)
        else:
            self.clicked.emit(self.page_num, event.modifiers())
    
    def enterEvent(self, event):
        super().enterEvent(event)
        self.glow_anim.stop()
        self.glow_anim.setEndValue(1.0)
        self.glow_anim.start()
    
    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.glow_anim.stop()
        self.glow_anim.setEndValue(0.0)
        self.glow_anim.start()

# ==========================================
# HOME VIEW
# ==========================================

class HomeView(QWidget):
    file_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        
        self.icon_label = QLabel("📄")
        self.icon_label.setStyleSheet("font-size: 80px;")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)
        
        title = QLabel("Gestor de Documentación Digital")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("INTRAMAQ S.A.S.")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(16)
        
        btn = AnimatedButton("📁  Seleccionar Archivo")
        btn.setObjectName("primaryButton")
        btn.clicked.connect(self._open_file)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def _open_file(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Seleccionar PDF(s)", "", "PDF Files (*.pdf)")
        if not paths:
            return
            
        if len(paths) == 1:
            self.file_selected.emit(paths[0])
        else:
            # Merge logic
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.parent().setWindowTitle("Fusionando PDFs... Por favor espere.")
            QApplication.processEvents()
            
            try:
                merged = merge_pdfs(paths)
                QApplication.restoreOverrideCursor()
                if merged:
                    self.file_selected.emit(merged)
                else:
                    QMessageBox.warning(self, "Error", "No se pudieron fusionar los archivos.")
            except Exception as e:
                QApplication.restoreOverrideCursor()
                QMessageBox.warning(self, "Error", str(e))
            finally:
                self.parent().setWindowTitle("ITMQ-GD v2.0.0 (dev) - Aero Edition")

# ==========================================
# EDITOR VIEW
# ==========================================

# ==========================================
# DIALOGS
# ==========================================
# FullPageDialog is now in app_shared

class TextResultDialog(QDialog):
    def __init__(self, engine, page_num, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Texto Detectado - Página {page_num + 1}")
        self.resize(600, 700)
        self.engine = engine
        self.page_num = page_num
        
        layout = QVBoxLayout(self)
        
        self.info_lbl = QLabel("Analizando documento... (Esto puede tardar unos segundos si es escaneado)")
        self.info_lbl.setWordWrap(True)
        self.info_lbl.setStyleSheet("color: #0078D4; font-weight: bold;")
        layout.addWidget(self.info_lbl)
        
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setStyleSheet("font-family: Consolas, monospace; font-size: 11pt;")
        layout.addWidget(self.text_area)
        
        btn_layout = QHBoxLayout()
        self.copy_btn = AnimatedButton("📋 Copiar al Portapapeles")
        self.copy_btn.clicked.connect(self._copy_text)
        self.close_btn = QPushButton("Cerrar")
        self.close_btn.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.copy_btn)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)
        
        # Start Analysis
        QTimer.singleShot(200, self._analyze)
        
    def _analyze(self):
        try:
            # 1. Try Native Text
            page = self.engine.doc.load_page(self.page_num)
            text = page.get_text("text")
            
            # Simple heuristic: If < 50 chars, probably an image/scanned
            if len(text.strip()) < 50:
                self.info_lbl.setText("📄 Texto digital escaso. Iniciando Motor IA (PaddleOCR)...")
                self.info_lbl.repaint()
                QApplication.processEvents() 
                
                # Check for PaddleOCR
                try:
                    from paddleocr import PaddleOCR
                    has_paddle = True
                except ImportError:
                    has_paddle = False
                
                # 2. Hybrid / Fallback OCR
                # Get High Res Image
                mat = fitz.Matrix(3.0, 3.0) 
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PIL first (Common for both)
                mode = "RGB" if pix.alpha == 0 else "RGBA"
                img_data = pix.samples
                from PIL import Image
                img = Image.frombytes(mode, [pix.width, pix.height], img_data)
                
                if has_paddle:
                    # Paddle prefers file paths for stability
                    import os
                    temp_img = f"temp_ocr_{self.page_num}.png"
                    img.save(temp_img) # Use PIL to save, it's robust
                    
                    try:
                        self.info_lbl.setText("🧠 Procesando con IA (Esto puede tardar la primera vez)...")
                        QApplication.processEvents()
                        
                        # Init Engine
                        ocr = PaddleOCR(use_angle_cls=True, lang='es')
                        result = ocr.ocr(temp_img, cls=True)
                        
                        # Parse Result
                        lines = []
                        if result and result[0]:
                            for line in result[0]:
                                lines.append(line[1][0])
                        
                        ocr_text = "\n".join(lines)
                        
                    finally:
                        if os.path.exists(temp_img):
                            os.remove(temp_img)
                            
                else:
                    # Fallback to Tesseract
                    self.info_lbl.setText("⚠️ Paddle no instalado. Usando Tesseract...")
                    QApplication.processEvents()
                    ocr_text = pytesseract.image_to_string(img, lang='spa+eng')
                
                if len(ocr_text.strip()) > len(text.strip()):
                    text = ocr_text
                    self.info_lbl.setText("✅ OCR Avanzado Completado.")
                else:
                    self.info_lbl.setText("⚠️ OCR completado pero no se encontró mucho texto.")
            else:
                self.info_lbl.setText("✅ Texto digital extraído.")
                
            self.text_area.setText(text)
            
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.info_lbl.setText(f"❌ Error: {str(e)}")
            self.text_area.setText(f"Error detallado: {e}\n\nTraceback:\n{tb}")
            
    def _copy_text(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text_area.toPlainText())
        QMessageBox.information(self, "Copiado", "Texto copiado al portapapeles.")

class DraggableScrollArea(QScrollArea):
    """
    ScrollArea that robustly handles dragging even over buttons.
    Uses EventFilter to intercept mouse events before the button consumes them.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("background: transparent; border: none;")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Physics State
        self._last_x = 0
        self._velocity = 0
        self._fricton = 0.88 # Slightly higher friction for less "slippery" feel
        self._timer = QTimer()
        self._timer.setInterval(16) # ~60 FPS
        self._timer.timeout.connect(self._inertia)
        self._is_dragging = False
        self._start_pos = 0
    
    def add_scroller_to(self, widget):
        """Install event filter on clickable widgets to enable drag"""
        widget.installEventFilter(self)

    def eventFilter(self, source, event):
        try:
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._last_x = event.globalPosition().x()
                    self._start_pos = event.globalPosition().x()
                    self._velocity = 0
                    self._is_dragging = False
                    self._timer.stop()
            
            elif event.type() == QEvent.Type.MouseMove:
                if event.buttons() & Qt.MouseButton.LeftButton:
                    curr_x = event.globalPosition().x()
                    delta = curr_x - self._last_x
                    
                    # Threshold to detect drag vs click (reduced for better sensitivity)
                    if not self._is_dragging and abs(curr_x - self._start_pos) > 5:
                        self._is_dragging = True
                    
                    if self._is_dragging:
                        # Scroll
                        bar = self.horizontalScrollBar()
                        bar.setValue(bar.value() - int(delta))
                        
                        self._velocity = delta # Capture simple velocity
                        self._last_x = curr_x
                        return True # Eat the event
                        
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton:
                    if self._is_dragging:
                        # Start inertia
                        self._timer.start()
                        return True # CRITICAL: Prevent the button from click
        except:
            pass # Safety for mismatched types
                
        return super().eventFilter(source, event)

    def _inertia(self):
        if abs(self._velocity) < 1:
            self._timer.stop()
            return
            
        bar = self.horizontalScrollBar()
        bar.setValue(bar.value() - int(self._velocity))
        self._velocity *= self._fricton

# ==========================================
# EDITOR VIEW
# ==========================================

class EditorView(QWidget):
    finished = pyqtSignal()
    page_selected = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = None
        self.categories = []
        self.segments = {}
        self.segment_list = []
        self.current_step = 0
        self.cards = []
        self.cat_buttons = {} # Cache for category buttons
        self.zoom_scale = 0.25
        self.cedula_data = None
        self.selected_indices = []
        self.last_clicked_idx = -1
        
        # Main Layout (Vertical: Grid Top, Bar Bottom)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Grid area (Takes all available space)
        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.grid_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setContentsMargins(20, 20, 20, 20)
        self.grid_scroll.setWidget(self.grid_widget)
        layout.addWidget(self.grid_scroll)
        
        # Bottom Bar (Auto-hiding, Vertical Container)
        self.bottom_bar = BottomBar()
        self.bottom_bar.set_expanded_size(160) # Increased to accommodate two rows
        
        # Main vertical container for the bottom bar rows
        bar_container_layout = QVBoxLayout()
        bar_container_layout.setContentsMargins(10, 5, 10, 5)
        bar_container_layout.setSpacing(5)
        self.bottom_bar.content_layout.addLayout(bar_container_layout)
        
        # --- ROW 1: Segments (Horizontal) ---
        self.segment_btn_layout = QHBoxLayout()
        self.segment_btn_layout.setSpacing(10)
        self.segment_btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bar_container_layout.addLayout(self.segment_btn_layout)
        self.segment_btns = []
        
        # --- ROW 2: Main Controls & Categories ---
        self.controls_row = QHBoxLayout()
        self.controls_row.setSpacing(10)
        bar_container_layout.addLayout(self.controls_row)
        
        # 2. Main Navigation Controls (Inside ROW 2)
        nav_controls = QWidget()
        nav_layout = QHBoxLayout(nav_controls)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(8)
        
        self.prev_seg_btn = AnimatedButton("⏮")
        self.prev_seg_btn.setFixedSize(40, 40)
        self.prev_seg_btn.setObjectName("smallBtn")
        self.prev_seg_btn.setToolTip("Segmento Anterior")
        self.prev_seg_btn.clicked.connect(self._prev_segment)
        nav_layout.addWidget(self.prev_seg_btn)
        
        self.prev_btn = AnimatedButton("←")
        self.prev_btn.setFixedSize(45, 45)
        self.prev_btn.setToolTip("Paso Anterior")
        self.prev_btn.clicked.connect(self._prev_step)
        nav_layout.addWidget(self.prev_btn)
        
        self.controls_row.addWidget(nav_controls)
        
        # 3. Horizontal Category List (Draggable Centerpiece)
        self.cat_scroll = DraggableScrollArea() 
        self.cat_scroll.setFixedHeight(60) 
        
        self.cat_widget = QWidget()
        self.cat_list = QHBoxLayout(self.cat_widget)
        self.cat_list.setContentsMargins(10, 0, 10, 0)
        self.cat_list.setSpacing(6)
        self.cat_scroll.setWidget(self.cat_widget)
        self.controls_row.addWidget(self.cat_scroll, stretch=10) # Heavy stretch
        
        # 4. Forward Controls
        fwd_controls = QWidget()
        fwd_layout = QHBoxLayout(fwd_controls)
        fwd_layout.setContentsMargins(5, 0, 5, 0)
        fwd_layout.setSpacing(8)
        
        self.next_btn = AnimatedButton("Siguiente →")
        self.next_btn.setMinimumWidth(120)
        self.next_btn.clicked.connect(self._next_step)
        fwd_layout.addWidget(self.next_btn)
        
        self.next_seg_btn = AnimatedButton("⏭")
        self.next_seg_btn.setFixedSize(40, 40)
        self.next_seg_btn.setObjectName("smallBtn")
        self.next_seg_btn.setToolTip("Siguiente Segmento")
        self.next_seg_btn.clicked.connect(self._next_segment)
        fwd_layout.addWidget(self.next_seg_btn)
        
        self.controls_row.addWidget(fwd_controls)
        
        # Vertical Separator
        self.sep_v2 = QFrame()
        self.sep_v2.setFrameShape(QFrame.Shape.VLine)
        self.sep_v2.setStyleSheet("color: rgba(128,128,128,0.3);")
        self.controls_row.addWidget(self.sep_v2)
        
        # 5. Tools (Zoom, Auto-Rotate, IA, Finish)
        tools_container = QWidget()
        tools_layout = QHBoxLayout(tools_container)
        tools_layout.setContentsMargins(10, 0, 10, 0)
        tools_layout.setSpacing(10)
        
        # Zoom group
        zoom_grp = QVBoxLayout()
        zoom_grp.setSpacing(0)
        zoom_icon = QLabel("🔍")
        zoom_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zoom_grp.addWidget(zoom_icon)
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setFixedWidth(80)
        self.zoom_slider.setRange(15, 50)
        self.zoom_slider.setValue(25)
        self.zoom_slider.valueChanged.connect(self._on_zoom_change)
        zoom_grp.addWidget(self.zoom_slider)
        tools_layout.addLayout(zoom_grp)
        
        # Action Buttons
        self.rotate_all_btn = AnimatedButton("🔄")
        self.rotate_all_btn.setFixedSize(40, 40)
        self.rotate_all_btn.setObjectName("accentButton")
        self.rotate_all_btn.setToolTip("Auto-Rotar Todo")
        self.rotate_all_btn.clicked.connect(self._auto_rotate)
        tools_layout.addWidget(self.rotate_all_btn)
        
        self.magic_btn = AnimatedButton("🪄")
        self.magic_btn.setFixedSize(40, 40)
        self.magic_btn.setObjectName("accentButton") 
        self.magic_btn.setToolTip("Auto-Clasificar IA")
        self.magic_btn.clicked.connect(self._auto_classify)
        tools_layout.addWidget(self.magic_btn)
        
        self.finish_btn = AnimatedButton("✓")
        self.finish_btn.setFixedSize(45, 45)
        self.finish_btn.setObjectName("primaryButton")
        self.finish_btn.setToolTip("Terminar y Guardar")
        self.finish_btn.clicked.connect(self._finish)
        tools_layout.addWidget(self.finish_btn)
        
        self.controls_row.addWidget(tools_container)
        
        layout.addWidget(self.bottom_bar)
    
    def load_pdf(self, path, profile_name=DEFAULT_PROFILE):
        # Cleanup previous engine & force GC
        if self.engine:
            self.engine.close()
            import gc
            gc.collect()
            
        profile = PROFILES[profile_name]
        self.engine = PDFEngine(path)
        self.categories = profile["CATEGORIES"]
        self.segments = profile.get("SEGMENTS", {})
        self.segment_list = list(self.segments.keys())
        self.current_step = 0
        self.current_segment_idx = 0
        self.results = {cat[0]: [] for cat in self.categories}
        
        self.segment_btns.clear()
        while self.segment_btn_layout.count():
            item = self.segment_btn_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self._create_cards()
        self._update_ui()
    
    def _create_cards(self):
        for c in self.cards:
            # We don't delete them, we just remove them from layout to re-add them
            pass
            
        # Clear/Delete existing cards if reloading
        # But here we are creating from scratch usually
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.cards.clear()
        
        if not self.engine:
            return
        
        # Instantiate cards but don't place them yet
        for i in range(self.engine.doc.page_count):
            card = PageCard(i, initial_scale=self.zoom_scale)
            card.clicked.connect(self._on_card_click)
            card.rotate_requested.connect(self._on_rotate)
            card.right_clicked.connect(self._on_right_click)
            card.set_image(self.engine.get_page_preview(i, self.zoom_scale))
            self.cards.append(card)
            
        # Calculate Layout
        self._reflow_grid()

    def resizeEvent(self, event):
        self._reflow_grid()
        super().resizeEvent(event)
        
    def _reflow_grid(self):
        if not self.cards:
            return
            
        # Get accessible width
        viewport_width = self.grid_scroll.viewport().width()
        if viewport_width < 100: viewport_width = 1000 # Fallback during init
        
        # Calculate card width (including spacing/margins approximation)
        card_w = self.cards[0].width() + 20 # +20 for spacing
        
        cols = max(1, viewport_width // card_w)
        
        # Remove all items from grid (without deleting widgets)
        for i in range(self.grid_layout.count()):
            self.grid_layout.takeAt(0)
            
        # Place ONLY VISIBLE cards
        visible_cards = [c for c in self.cards if not c.hidden]
        for i, card in enumerate(visible_cards):
            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(card, row, col)

    def _on_card_click(self, page_num, modifiers):
        # 1. Selection Logic
        if modifiers & Qt.KeyboardModifier.ShiftModifier and self.last_clicked_idx != -1:
            # Range Selection
            start = min(self.last_clicked_idx, page_num)
            end = max(self.last_clicked_idx, page_num)
            for i in range(start, end + 1):
                if i not in self.selected_indices:
                    self.selected_indices.append(i)
        elif modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier):
            # Toggle Selection
            if page_num in self.selected_indices:
                self.selected_indices.remove(page_num)
            else:
                self.selected_indices.append(page_num)
        else:
            # Standard click: toggle self and clear others OR just select this one
            # To preserve existing behavior of "one-by-one" but allow batch,
            # we can make single click assign to current category IF nothing else is selected?
            # User wants Batch EDIT, so let's make it robust:
            if page_num in self.selected_indices and len(self.selected_indices) == 1:
                self.selected_indices = []
            else:
                self.selected_indices = [page_num]
        
        self.last_clicked_idx = page_num
        
        # 2. Assignment Logic (preserving current step behavior if single clicked or batch trigger)
        # If we have multiple selections, we DON'T automatically assign because user might beSelecting.
        # But if they single clicked without modifiers, maybe they WANT to assign.
        # HOWEVER, the best UX for batch is: Select many -> click category button.
        
        # For now, let's keep it so a single click without modifiers STILL assigns to the CURRENT STEP
        # This preserves the "fast mode" while enabling "batch mode" via buttons or context menu later.
        if not modifiers:
             self._assign_category(page_num, self.categories[self.current_step][0])
        
        self.page_selected.emit()
        self._update_ui()

    def _assign_category(self, page_num, abbr):
        # Prevent double assignment to same cat
        if page_num in self.results[abbr]:
            self.results[abbr].remove(page_num)
            return

        # Check if Cédula step - show dialog
        if abbr == "CC" and not self.cedula_data:
            dialog = CedulaDialog(self.engine, page_num, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.cedula_data = dialog.result_data
            else:
                return
        
        self.results[abbr].append(page_num)
        
        # LEARN (Active Training)
        try:
            page = self.engine.doc.load_page(page_num)
            text = page.get_text("text")
            if len(text.strip()) > 30:
                ModelManager().learn(text, abbr)
        except:
            pass
    
    def _auto_rotate(self):
        """Analyze all pages using Tesseract OSD and fix orientation"""
        if not self.engine: return
        
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.rotate_all_btn.setText("⏳ ...")
        QApplication.processEvents()
        
        changes = 0
        try:
            from PIL import Image
            import pytesseract
            import re
            import io
            
            count = len(self.cards)
            for i, card in enumerate(self.cards):
                # We analyze the PREVIEW because it reflects current rotation
                # Use slightly higher res for OSD
                pix = self.engine.get_page_preview(i, scale=1.5)
                
                # Convert to PIL
                buffer = QBuffer()
                buffer.open(QIODevice.OpenModeFlag.ReadWrite)
                pix.save(buffer, "PNG")
                pil_im = Image.open(io.BytesIO(buffer.data()))
                
                try:
                    osd = pytesseract.image_to_osd(pil_im, lang='eng') # OSD works best with eng or osd
                    # Parse "Rotate: 180" or "Orientation in degrees: 180"
                    # 'Rotate' usually tells us how much to rotate CW to fix it.
                    rot_match = re.search(r"Rotate: (\d+)", osd)
                    if rot_match:
                        rotation_needed = int(rot_match.group(1))
                        
                        times = 0
                        if rotation_needed == 90: times = 1
                        elif rotation_needed == 180: times = 2
                        elif rotation_needed == 270: times = 3
                        
                        if times > 0:
                            for _ in range(times):
                                self.engine.rotate_page(i)
                            
                            # Update card image
                            card.set_image(self.engine.get_page_preview(i, self.zoom_scale))
                            changes += 1
                            QApplication.processEvents()
                except:
                    pass 
            
            if changes > 0:
                QMessageBox.information(self, "Auto-Rotación", f"Se han enderezado {changes} páginas.")
            else:
                QMessageBox.information(self, "Auto-Rotación", "Todas las páginas parecen estar rectas.")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Fallo en Auto-Rotación: {str(e)}")
            
        finally:
            QApplication.restoreOverrideCursor()
            self.rotate_all_btn.setText("🔄 Auto-Rotar")

    def _auto_classify(self):
        if not self.engine: return
        
        mgr = ModelManager()
        if not mgr.model:
            QMessageBox.information(self, "IA no entrenada", "Primero clasifica manualmente algunos documentos (aprox 5-10) para que aprenda.")
            return
            
        self.magic_btn.setText("⏳ ...")
        QApplication.processEvents()
        
        count = 0
        try:
            # Predict for ALL pages that are not categorized?
            # Or just iterate all.
            for i, card in enumerate(self.cards):
                # Extract text
                page = self.engine.doc.load_page(i)
                text = page.get_text("text")
                
                if len(text.strip()) > 20:
                    pred_abbr = mgr.predict(text)
                    if pred_abbr: # Will apply strict null check from ai_core
                        # Add to result if not present
                        if pred_abbr not in self.results: self.results[pred_abbr] = []
                        if i not in self.results[pred_abbr]:
                            self.results[pred_abbr].append(i)
                            count += 1
            
            self._update_ui()
            if count > 0:
                QMessageBox.information(self, "Auto-Clasificación", f"¡He clasificado {count} páginas automáticamente!")
            else:
                QMessageBox.information(self, "Sin coincidencias", "No encontré similitudes claras o estoy insegura. Sigue enseñándome.")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            
        self.magic_btn.setText("🪄 Auto")
    
    def _on_rotate(self, page_num):
        if self.engine:
            self.engine.rotate_page(page_num)
            self.cards[page_num].set_image(self.engine.get_page_preview(page_num, self.zoom_scale))
    
    def _on_right_click(self, page_num):
        """Immediately open high-res preview on right click"""
        if not self.engine:
            return
            
        dialog = FullPageDialog(self.engine, page_num, self)
        dialog.exec()
        
        # Refresh card in case rotation occurred (though dialog doesn't currently rotate, for future-proofing)
        if self.engine:
            self.cards[page_num].set_image(self.engine.get_page_preview(page_num, self.zoom_scale))
    
    def _on_zoom_change(self, value):
        self.zoom_scale = value / 100.0
        for card in self.cards:
            if self.engine:
                card.update_zoom(self.zoom_scale)
                # Refetch scaled image for better quality
                card.set_image(self.engine.get_page_preview(card.page_num, self.zoom_scale))
        self._reflow_grid()
    
    # Removed _on_segment_change
    
    def _prev_segment(self):
        if self.current_segment_idx > 0:
            self._jump_to_segment(self.current_segment_idx - 1)
    
    def _next_segment(self):
        if self.current_segment_idx < len(self.segment_list) - 1:
            self._jump_to_segment(self.current_segment_idx + 1)
    
    def _prev_step(self):
        if self.current_step > 0:
            self.current_step -= 1
            self._update_ui()
    
    def _next_step(self):
        if self.current_step < len(self.categories) - 1:
            self.current_step += 1
            self._update_ui()
    
    def _finish(self):
        # 1. Validation & Data Gathering
        cedula = ""
        nombre = ""
        apellido = ""
        
        # Check if we have data from CedulaDialog
        if self.cedula_data:
            cedula = self.cedula_data.get("cedula", "")
        
        # If missing, ask user
        if not cedula:
            text, ok = QInputDialog.getText(self, "Datos del Paciente", "Ingrese el Número de Cédula:")
            if ok and text: cedula = text.strip()
            else: return # Cancelled
            
        # Get Name/Surname (Simplified: Single Prompt or separate?)
        # Let's verify if we have them or ask
        text, ok = QInputDialog.getText(self, "Datos del Paciente", "Ingrese Apellidos y Nombres (Ej: Perez Juan):")
        if ok and text:
            parts = text.strip().split()
            if len(parts) >= 2:
                apellido = parts[0]
                nombre = " ".join(parts[1:])
            else:
                apellido = text.strip()
                nombre = "X"
        else:
            return # Cancelled
            
        # 2. Create Directory Structure
        # Format: [APELLIDO] [NOMBRE] [CEDULA]
        folder_name = f"{apellido} {nombre} {cedula}".strip()
        # Clean invalid chars
        folder_name = "".join([c for c in folder_name if c.isalnum() or c in (' ', '-', '_')])
        
        import os
        desktop = os.path.expanduser("~/Desktop")
        base_dir = os.path.join(desktop, folder_name)
        hl_dir = os.path.join(base_dir, "HISTORIA LABORAL")
        
        try:
            os.makedirs(hl_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo crear la carpeta: {e}")
            return

        # 3. Process & Save Files
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.finish_btn.setText("Guardando...")
        QApplication.processEvents()
        
        log_lines = []
        log_lines.append(f"REGISTRO DE CLASIFICACIÓN")
        log_lines.append(f"FECHA: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log_lines.append(f"PACIENTE: {apellido} {nombre}")
        log_lines.append(f"CEDULA: {cedula}")
        log_lines.append("-" * 30)
        log_lines.append("ARCHIVOS GENERADOS:")
        
        try:
            count_saved = 0
            # Iterate categories to save
            for abbr, pages in self.results.items():
                if not pages: continue
                
                # Sort pages
                pages.sorted_pages = sorted(pages)
                
                # Save to PDF
                # Filename: [ABBR]_[CEDULA].pdf ? Or just [ABBR].pdf?
                # User said "archivos abreviados con la respectiva cedula"
                filename = f"{abbr}_{cedula}.pdf"
                out_path = os.path.join(hl_dir, filename)
                
                # Use FitZ to save subset
                import fitz
                doc = fitz.open()
                src_doc = self.engine.doc
                for p in pages.sorted_pages:
                    doc.insert_pdf(src_doc, from_page=p, to_page=p)
                
                doc.save(out_path)
                doc.close()
                
                log_lines.append(f"[OK] {filename} ({len(pages)} páginas)")
                count_saved += 1
            
            # List missing
            log_lines.append("-" * 30)
            log_lines.append("CATEGORÍAS FALTANTES:")
            for abbr, name in self.categories:
                if not self.results.get(abbr):
                    log_lines.append(f"[FALTA] {name} ({abbr})")
            
            # 4. Save Log
            log_path = os.path.join(base_dir, f"registro_{cedula}.txt")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("\n".join(log_lines))
                
            QApplication.restoreOverrideCursor()
            
            # Open folder
            os.startfile(base_dir)
            
            QMessageBox.information(self, "Proceso Completado", f"Se guardaron {count_saved} archivos en:\n{base_dir}")
            self.finished.emit()
            
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error Fatal", f"Error al guardar archivos: {str(e)}")
        finally:
            self.finish_btn.setText("✓")
    
    def _update_ui(self):
        if not self.categories:
            return
        
        abbr, name = self.categories[self.current_step]
        
        self._update_segment_buttons()
        self._update_category_list()
        
        # Get all assigned pages (for hiding)
        all_assigned = set()
        for k, v in self.results.items():
            if k != abbr:
                all_assigned.update(v)
        
        # Update cards
        for card in self.cards:
            # Hide if assigned elsewhere
            card.set_hidden(card.page_num in all_assigned)
            
            # Selection state
            if card.page_num in self.results[abbr]:
                idx = self.results[abbr].index(card.page_num) + 1
                card.set_selected(True, f"#{idx}")
            else:
                card.set_selected(False)
        
        self.prev_btn.setEnabled(self.current_step > 0)
        self.prev_seg_btn.setEnabled(self.current_segment_idx > 0)
        self.next_seg_btn.setEnabled(self.current_segment_idx < len(self.segment_list) - 1)
        
        is_last = self.current_step == len(self.categories) - 1
        self.next_btn.setText("→ Último" if is_last else "Siguiente →")
        
        # Trigger grid reflow to reorganize items
        self._reflow_grid()
    
    def _update_category_list(self):
        if not self.categories: return
        
        seg_idx = self.current_segment_idx
        if seg_idx < 0: return 
        
        visible_abbrs = self.segments.get(self.segment_list[seg_idx], [])
        active_abbr, _ = self.categories[self.current_step]
        
        # Check if we need to initialize buttons
        if not self.cat_buttons:
            for idx, (abbr, name) in enumerate(self.categories):
                btn = AnimatedButton(f"{name} (0)")
                btn.setCheckable(True)
                btn.setObjectName("navButton")
                btn.setFixedHeight(40)
                btn.clicked.connect(lambda _, i=idx: self._set_step(i))
                
                # IMPORTANT: Add scroller filter to enable drag on buttons
                self.cat_scroll.add_scroller_to(btn)
                
                self.cat_list.addWidget(btn)
                self.cat_buttons[abbr] = btn
        
        # Update visibility and state
        for idx, (abbr, name) in enumerate(self.categories):
            btn = self.cat_buttons[abbr]
            is_visible = abbr in visible_abbrs
            btn.setVisible(is_visible)
            
            if is_visible:
                count = len(self.results.get(abbr, []))
                # Highlight if selected
                if idx == self.current_step:
                    btn.setChecked(True)
                    btn.setText(f"● {name} ({count})")
                else:
                    btn.setChecked(False)
                    btn.setText(f"{name} ({count})")
        
        # Force centering of active button with a tiny delay to ensure layout is ready
        if active_abbr in self.cat_buttons:
             target_btn = self.cat_buttons[active_abbr]
             QTimer.singleShot(100, lambda: self._ensure_button_centered(target_btn))

    def _update_segment_buttons(self):
        # Dynamically create buttons for segments in a horizontal row
        if not self.segment_btns:
            for i, seg_name in enumerate(self.segment_list):
                btn = AnimatedButton("") # Text set dynamically below
                btn.setCheckable(True)
                btn.setObjectName("segmentBtn") # Specialized naming
                btn.clicked.connect(lambda _, idx=i: self._jump_to_segment(idx))
                self.segment_btn_layout.addWidget(btn)
                self.segment_btns.append(btn)
        
        # Update checked state AND text dynamically
        for i, btn in enumerate(self.segment_btns):
            is_active = (i == self.current_segment_idx)
            btn.setChecked(is_active)
            
            seg_name = self.segment_list[i]
            # Logic: Full name if active, Prefix if not
            if is_active:
                btn.setText(seg_name)
                btn.setMinimumWidth(100)
                btn.setStyleSheet("font-weight: bold; padding: 5px 15px; border-radius: 15px;")
            else:
                # Get the letter prefix (e.g. 'A' from 'A. Contrato')
                prefix = seg_name.split('.')[0] if '.' in seg_name else seg_name[:1]
                btn.setText(prefix)
                btn.setMinimumWidth(30)
                btn.setStyleSheet("font-weight: 500; padding: 5px; border-radius: 15px;")

    def _jump_to_segment(self, idx):
        self.current_segment_idx = idx
        # Find first category of this segment
        seg_name = self.segment_list[idx]
        cat_abbrs = self.segments.get(seg_name, [])
        if cat_abbrs:
             first_abbr = cat_abbrs[0]
             # Find index in self.categories
             for i, (abbr, _) in enumerate(self.categories):
                 if abbr == first_abbr:
                     self.current_step = i
                     break
        self._update_ui()
    def _set_step(self, idx):
        self.current_step = idx
        self._update_ui()
            
    def _ensure_button_centered(self, btn):
        """Smoothly scroll to center the given button"""
        if not btn or not btn.isVisible(): return
        
        # Ensure latest geometry is calculated
        self.cat_widget.adjustSize()
        
        scroll_bar = self.cat_scroll.horizontalScrollBar()
        container_width = self.cat_scroll.viewport().width()
        
        if container_width <= 0: return # Component not ready
        
        # Calculate target position to center the button
        # btn.x() is relative to cat_widget
        btn_center = btn.x() + btn.width() // 2
        target_scroll = btn_center - container_width // 2
        
        # Clamp value
        target_scroll = max(0, min(target_scroll, scroll_bar.maximum()))
        
        # Animate smoothly
        if not hasattr(self, "_anim_scroll"):
            self._anim_scroll = QPropertyAnimation(scroll_bar, b"value")
            self._anim_scroll.setDuration(500) 
            self._anim_scroll.setEasingCurve(QEasingCurve.Type.OutCubic)
            
        self._anim_scroll.stop()
        self._anim_scroll.setStartValue(scroll_bar.value())
        self._anim_scroll.setEndValue(target_scroll)
        self._anim_scroll.start()

# ==========================================
# SETTINGS VIEW
# ==========================================

class SettingsView(QWidget):
    theme_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        tm = get_theme_manager()

        title = QLabel("Configuración")
        title.setObjectName("title")
        layout.addWidget(title)
        
        layout.addWidget(QLabel("Perfil de Categorías"))
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(PROFILES.keys())
        layout.addWidget(self.profile_combo)
        
        # Theme section with separator
        theme_label = QLabel("Estética y Temas")
        theme_label.setStyleSheet("font-size: 16px; font-weight: 600; margin-top: 10px;")
        layout.addWidget(theme_label)
        
        # Auto Sync Option (Now a Toggle)
        self.auto_btn = AnimatedButton("🔄 Sincronizar con Windows")
        self.auto_btn.setCheckable(True)
        self.auto_btn.setChecked(tm.auto_theme)
        self.auto_btn.clicked.connect(self._toggle_auto)
        layout.addWidget(self.auto_btn)
        
        # Theme Mode row
        mode_label = QLabel("Tema de Fondo")
        mode_label.setStyleSheet("font-size: 14px; font-weight: 500; color: #666; margin-top: 10px;")
        layout.addWidget(mode_label)
        
        mode_row = QHBoxLayout()
        self.light_btn = AnimatedButton("☀️ Claro")
        self.light_btn.setCheckable(True)
        self.light_btn.clicked.connect(lambda: self._set_mode("light"))
        mode_row.addWidget(self.light_btn)
        
        self.dark_btn = AnimatedButton("🌙 Oscuro")
        self.dark_btn.setCheckable(True)
        self.dark_btn.clicked.connect(lambda: self._set_mode("dark"))
        mode_row.addWidget(self.dark_btn)
        layout.addLayout(mode_row)
        
        # Transparency Mode (Effect Material)
        eff_label = QLabel("Material de Fondo")
        eff_label.setStyleSheet("font-size: 14px; font-weight: 500; color: #666; margin-top: 10px;")
        layout.addWidget(eff_label)
        
        eff_row = QHBoxLayout()
        self.mica_btn = AnimatedButton("🪟 Mica (Opaco)")
        self.mica_btn.setCheckable(True)
        self.mica_btn.clicked.connect(lambda: self._set_transparency_mode("mica"))
        eff_row.addWidget(self.mica_btn)
        
        self.acrylic_btn = AnimatedButton("✨ Acrylic (Cristal)")
        self.acrylic_btn.setCheckable(True)
        self.acrylic_btn.clicked.connect(lambda: self._set_transparency_mode("acrylic"))
        eff_row.addWidget(self.acrylic_btn)
        layout.addLayout(eff_row)
        
        # Info label
        self.info_label = QLabel("💡 Mica: Efecto nativo sutil de Windows 11.\n✨ Acrylic: Efecto translúcido difuminado (ajustable).")
        self.info_label.setStyleSheet("color: #888; font-size: 11px; font-style: italic;")
        layout.addWidget(self.info_label)
        
        # Transparency adjustment (Only for Acrylic)
        trans_layout = QVBoxLayout()
        trans_label = QLabel("🔆 Opacidad del Cristal (Solo Acrylic)")
        trans_label.setStyleSheet("font-size: 14px; font-weight: 600; margin-top: 15px; color: #0078D4;")
        trans_layout.addWidget(trans_label)
        
        self.trans_slider = QSlider(Qt.Orientation.Horizontal)
        self.trans_slider.setRange(20, 240)
        self.trans_slider.setValue(tm.transparency_level)
        self.trans_slider.valueChanged.connect(self._on_transparency_change)
        trans_layout.addWidget(self.trans_slider)
        
        trans_info = QLabel("Más Transparencia ← → Más Opacidad")
        trans_info.setStyleSheet("font-size: 11px; color: #888;")
        trans_layout.addWidget(trans_info)
        layout.addLayout(trans_layout)
        
        layout.addStretch()
        
        # Initial State Sync
        self._update_buttons()
    
    def _on_transparency_change(self, value):
        tm = get_theme_manager()
        tm.transparency_level = value
        self.theme_changed.emit()
    
    def _toggle_auto(self, checked):
        tm = get_theme_manager()
        tm.auto_theme = checked
        self._update_buttons()
        self.theme_changed.emit()

    def _set_mode(self, mode):
        tm = get_theme_manager()
        tm.theme_mode = mode
        self._update_buttons()
        self.theme_changed.emit()

    def _set_transparency_mode(self, mode):
        tm = get_theme_manager()
        tm.transparency_mode = mode
        self._update_buttons()
        self.theme_changed.emit()
        
    def _update_buttons(self):
        tm = get_theme_manager()
        # Sync all buttons with global state
        self.auto_btn.setChecked(tm.auto_theme)
        
        # Enable/Disable based on auto
        btns = [self.light_btn, self.dark_btn, self.mica_btn, self.acrylic_btn]
        for btn in btns:
            btn.setEnabled(not tm.auto_theme)
            
        if not tm.auto_theme:
            self.light_btn.setChecked(tm.theme_mode == "light")
            self.dark_btn.setChecked(tm.theme_mode == "dark")
            
            self.mica_btn.setChecked(tm.transparency_mode == "mica")
            self.acrylic_btn.setChecked(tm.transparency_mode == "acrylic")
            
        # Slider only enabled for Acrylic
        is_acrylic = tm.transparency_mode == "acrylic" and not tm.auto_theme
        self.trans_slider.setEnabled(is_acrylic)

# ==========================================
# HELP VIEW
# ==========================================

class HelpView(QWidget):
    tutorial_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        
        title = QLabel("Ayuda")
        title.setObjectName("title")
        layout.addWidget(title)
        
        help_text = """
        <h3 style="color: #4F46E5;">Controles</h3>
        <p>• <b>Clic izquierdo</b>: Seleccionar/deseleccionar página</p>
        <p>• <b>Clic derecho</b>: Ver página en alta resolución</p>
        <p>• <b>↻</b>: Rotar página 90° en sentido del reloj</p>
        <p>• <b>Slider</b>: Ajustar zoom de miniaturas</p>
        <h3 style="color: #4F46E5;">Navegación</h3>
        <p>• <b>⏮ Seg / Seg ⏭</b>: Saltar entre segmentos</p>
        <p>• <b>← Anterior / Siguiente →</b>: Cambiar categoría</p>
        """
        help_label = QLabel(help_text)
        help_label.setWordWrap(True)
        help_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(help_label)
        
        layout.addSpacing(30)
        
        self.tut_btn = AnimatedButton("🚀 Iniciar Tutorial Interactivo")
        self.tut_btn.setObjectName("primaryButton")
        self.tut_btn.clicked.connect(self.tutorial_requested.emit)
        layout.addWidget(self.tut_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        
        layout.addStretch()

# ==========================================
# INTERACTIVE TUTORIAL
# ==========================================

class TutorialStep:
    def __init__(self, target_widget, text, align="bottom", trigger_signal=None, demo_action=None):
        self.target_widget = target_widget
        self.text = text
        self.align = align
        self.trigger_signal = trigger_signal # Name of signal to wait for
        self.demo_action = demo_action # Optional function to run when step starts

class TutorialOverlay(QWidget):
    finished = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setVisible(False)
        
        self.steps = []
        self.current_step = 0
        self._step_initialized = False
        
        self.msg_box = QFrame(self)
        self.msg_box.setObjectName("tutorialBox")
        self.msg_box.setStyleSheet("""
            #tutorialBox {
                background-color: #4F46E5;
                border-radius: 12px;
                padding: 20px;
            }
            QLabel { color: white; border: none; background: transparent; }
        """)
        self.msg_layout = QVBoxLayout(self.msg_box)
        
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setStyleSheet("font-size: 16px; font-weight: 500;")
        self.msg_layout.addWidget(self.label)
        
        self.next_btn = AnimatedButton("Siguiente →")
        self.next_btn.clicked.connect(self._next_step)
        self.msg_layout.addWidget(self.next_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        # New interaction label
        self.hint_label = QLabel()
        self.hint_label.setStyleSheet("font-size: 13px; font-style: italic; color: #D1D5DB; margin-top: 5px;")
        self.hint_label.setVisible(False)
        self.msg_layout.addWidget(self.hint_label)
        
        # Shadow for msg_box
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0,0,0,80))
        shadow.setOffset(0, 5)
        self.msg_box.setGraphicsEffect(shadow)

        # Refresh timer for dynamic positioning
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(16) # 60 FPS
        self.refresh_timer.timeout.connect(self._update_display)

    def start(self, steps):
        self.steps = steps
        self.current_step = 0
        self._step_initialized = False
        self.show()
        self.raise_()
        self.refresh_timer.start()
        # Cover whole parent
        if self.parent():
            self.setGeometry(0, 0, self.parent().width(), self.parent().height())
        self._update_display()
        
    def _update_display(self):
        if self.current_step >= len(self.steps):
            self.hide()
            self.refresh_timer.stop()
            self.finished.emit()
            return
            
        step = self.steps[self.current_step]
        
        # ONE-TIME STEP INITIALIZATION
        if not self._step_initialized:
            self.label.setText(step.text)
            
            # Run demo action if any
            if step.demo_action:
                step.demo_action()

            # Handle Interaction Requirement
            if step.trigger_signal and step.target_widget:
                self.next_btn.setEnabled(False)
                self.next_btn.setText("Esperando acción...")
                self.hint_label.setText("💡 Realice la acción resaltada para continuar")
                self.hint_label.setVisible(True)
                
                # Dynamically connect to signal
                try:
                    sig = getattr(step.target_widget, step.trigger_signal)
                    sig.connect(self._on_action_completed)
                    self._current_sig_connection = (sig, self._on_action_completed)
                except Exception as e:
                    print(f"Tutorial signal connection error: {e}")
                    self.next_btn.setEnabled(True)
            else:
                self.next_btn.setEnabled(True)
                self.hint_label.setVisible(False)
                if self.current_step == len(self.steps) - 1:
                    self.next_btn.setText("¡Entendido!")
                else:
                    self.next_btn.setText("Siguiente →")
            
            self._step_initialized = True
            
        # Position & Alignment Logic
        target = step.target_widget
        if target:
            # PROACTIVE AUTO-EXPAND: If target is in an AutoDrawer, ensure it starts expanding
            p = target.parent()
            while p:
                from app_shared import AutoDrawer
                if isinstance(p, AutoDrawer):
                    if not p.is_expanded:
                        p._start_anim(True) # Force expansion
                    break
                p = p.parent()

        if target and target.isVisible():
            # SYNC GEOMETRY: Always cover parent during animations
            if self.parent() and self.geometry() != self.parent().rect():
                self.setGeometry(self.parent().rect())

            # PRECISE COORDINATE MAPPING
            global_pos = target.mapToGlobal(QPoint(0,0))
            local_pos = self.mapFromGlobal(global_pos)
            
            # center box relative to widget or fixed
            self.msg_box.setFixedWidth(300)
            self.msg_box.adjustSize()

            # Logic to place box near target
            bx = local_pos.x() + (step.target_widget.width() // 2) - (self.msg_box.width() // 2)
            
            if step.align == "bottom":
                by = local_pos.y() + step.target_widget.height() + 20
            else: # top
                by = local_pos.y() - self.msg_box.height() - 20
            
            # Constraints
            bx = max(20, min(bx, self.width() - self.msg_box.width() - 20))
            by = max(20, min(by, self.height() - self.msg_box.height() - 20))
            
            self.msg_box.move(bx, by)
        else:
            # Centered if no target or hidden
            self.msg_box.setFixedWidth(400)
            self.msg_box.adjustSize()
            self.msg_box.move((self.width() - self.msg_box.width()) // 2, (self.height() - self.msg_box.height()) // 2)
            
        self.update()
        
    def _get_highlight_rect(self):
        step = self.steps[self.current_step]
        if step.target_widget and step.target_widget.isVisible():
            global_pos = step.target_widget.mapToGlobal(QPoint(0,0))
            local_pos = self.mapFromGlobal(global_pos)
            return QRect(local_pos.x() - 5, local_pos.y() - 5, 
                         step.target_widget.width() + 10, 
                         step.target_widget.height() + 10)
        return None

    def mousePressEvent(self, event):
        # Click passthrough for the hole
        rect = self._get_highlight_rect()
        if rect and rect.contains(event.pos()):
            # If clicked inside the hole, IGNORE the event so it goes through to the widget below
            event.ignore()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # New robust path-based hole drawing
        path = QPainterPath()
        path.addRect(QRectF(self.rect())) # Outside area
        
        highlight_rect = self._get_highlight_rect()
        if highlight_rect:
            # Add hole to the path (using OddEvenFill rule)
            hole_path = QPainterPath()
            hole_path.addRoundedRect(QRectF(highlight_rect), 10, 10)
            path = path.subtracted(hole_path)
            
            # Draw highlight accent border SEPARATELY
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            t = get_theme()
            painter.setPen(QPen(QColor(t['primary']), 3))
            painter.drawRoundedRect(highlight_rect, 10, 10)
            
        # Draw the darkened overlay (everything EXCEPT the hole)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.setBrush(QBrush(QColor(0, 0, 0, 160)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)

    def _on_action_completed(self):
        # Disconnect to prevent multiple triggers
        if hasattr(self, "_current_sig_connection"):
            sig, slot = self._current_sig_connection
            try:
                sig.disconnect(slot)
            except: pass
            delattr(self, "_current_sig_connection")
            
        self.next_btn.setEnabled(True)
        self.next_btn.setText("¡Muy bien! Siguiente →")
        self.hint_label.setVisible(False)

    def _next_step(self):
        # Prevent manual skip if action is required
        step = self.steps[self.current_step]
        if step.trigger_signal and not self.next_btn.isEnabled():
            return
            
        self.current_step += 1
        self._step_initialized = False # Force setup for next step
        self._update_display()
        
    def resizeEvent(self, event):
        if self.parent():
            self.setGeometry(0, 0, self.parent().width(), self.parent().height())
        super().resizeEvent(event)

# ==========================================
# MAIN WINDOW
# ==========================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        status = itmq_license.get_license_status_text()
        self.setWindowTitle(f"ITMQ-GD v2.0.0 (dev) ({status})")
        self.setMinimumSize(1280, 800)
        
        # IMPORTANT: Set translucent background MANDATORY for Acrylic/Mica
        if is_drawing_glass():
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            # This ensures that the window composition survives re-applying themes
            self.setAutoFillBackground(False)
        
        # Central widget with horizontal layout for Sidebar + Content
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar Navigation Pane (Auto-hiding Sliding SideBar)
        self.sidebar = SideBar()
        
        # Sidebar Header
        sidebar_title = QLabel("INTRAMAQ S.A.S.")
        sidebar_title.setObjectName("title")
        sidebar_title.setStyleSheet("font-size: 22px; margin-bottom: 20px; padding-left: 10px;")
        self.sidebar.addWidget(sidebar_title)
        
        # Navigation Buttons Group
        self.nav_buttons = []
        nav_items = [
            ("🏠 Inicio", 0),
            ("📁 Editor", 1),
            ("⚙️ Configuración", 2),
            ("❓ Ayuda", 3)
        ]
        
        for text, idx in nav_items:
            btn = AnimatedButton(text)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, i=idx: self._switch_tab(i))
            self.sidebar.addWidget(btn)
            self.nav_buttons.append(btn)
        
        self.sidebar.addStretch()
        
        # Profile selector at bottom of sidebar
        profile_label = QLabel("Perfil Activo")
        profile_label.setStyleSheet("font-size: 11px; font-weight: 700; color: #888; margin-top: 10px; padding-left: 10px;")
        self.sidebar.addWidget(profile_label)
        
        self.side_profile_combo = QComboBox()
        self.side_profile_combo.addItems(PROFILES.keys())
        self.sidebar.addWidget(self.side_profile_combo)
        
        main_layout.addWidget(self.sidebar)
        
        # Content Area
        self.stack = FadeStackedWidget()
        main_layout.addWidget(self.stack, 1)
        
        self.home_view = HomeView()
        self.home_view.file_selected.connect(self._on_file_selected)
        self.stack.addWidget(self.home_view)
        
        self.editor_view = EditorView()
        self.stack.addWidget(self.editor_view)
        
        self.settings_view = SettingsView()
        self.settings_view.theme_changed.connect(self._apply_theme)
        # Sync side combo with settings combo
        self.side_profile_combo.currentTextChanged.connect(self.settings_view.profile_combo.setCurrentText)
        self.settings_view.profile_combo.currentTextChanged.connect(self.side_profile_combo.setCurrentText)
        self.stack.addWidget(self.settings_view)
        
        self.help_view = HelpView()
        self.help_view.tutorial_requested.connect(self._run_tutorial)
        self.stack.addWidget(self.help_view)
        
        # Tutorial Overlay
        self.tutorial = TutorialOverlay(self)
        
        # Initialize selection
        self._switch_tab(0)
        
        # Check first run (simplified for demo, usually from user_settings.json)
        QTimer.singleShot(2000, self._check_first_run)
        
        # Initialize Theme Watcher
        self.watcher = ThemeWatcher(self._on_system_theme_changed)
        self.watcher.start()
        
        self._apply_theme()
        self.showMaximized()

    def _switch_tab(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
    
    def _on_system_theme_changed(self, is_dark):
        """Callback for when Windows theme changes"""
        tm = get_theme_manager()
        if tm.auto_theme:
            # We need to use a timer or signal to update UI from a non-GUI thread
            QTimer.singleShot(0, self._apply_theme)
    
    def _on_file_selected(self, path):
        profile = self.side_profile_combo.currentText() # Use side combo for profile
        self.editor_view.load_pdf(path, profile)
        # Switch to Editor tab (index 1)
        self._switch_tab(1)
    
    def _load_tutorial_demo(self):
        """Creates a dummy PDF if none is loaded for the tutorial"""
        if self.editor_view.engine: return
        
        import fitz
        # Create a tiny 1-page PDF
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Este es un documento de prueba para el Tutorial de GDD.")
        page.insert_text((50, 100), "Sigue las instrucciones para aprender a clasificar.")
        
        temp_path = os.path.join(os.environ.get("TEMP", "."), "tutorial_demo.pdf")
        doc.save(temp_path)
        doc.close()
        
        self._on_file_selected(temp_path)
    
    def _check_first_run(self):
        settings = load_settings()
        if settings.get("tutorial_completed", False) is False:
            self._run_tutorial()
            settings["tutorial_completed"] = True
            save_settings(settings)

    def _run_tutorial(self):
        # Go to home first
        self._switch_tab(0)
        
        steps = [
            TutorialStep(None, "¡Bienvenido al nuevo Tutorial Interactivo de GDD! Vamos a practicar juntos."),
            TutorialStep(self.sidebar, "Este es el panel lateral. Al pasar el ratón se abrirá automáticamente para mostrar las opciones."),
            TutorialStep(self.nav_buttons[1], "Ahora haz clic en 'Editor' para continuar con el proceso de prueba.", 
                         trigger_signal="clicked", demo_action=None),
            TutorialStep(None, "Excelente. Ahora cargaremos un documento de prueba automáticamente para que puedas interactuar.",
                         demo_action=self._load_tutorial_demo),
            TutorialStep(self.editor_view.cat_scroll, "Aquí están las categorías. Puedes desplazarlas con el ratón o deslizando."),
            TutorialStep(self.editor_view, "Estas son las páginas del documento. Haz clic en una página para seleccionarla.",
                         trigger_signal="page_selected"),
            TutorialStep(self.editor_view.next_btn, "Al seleccionar, se asigna a la categoría actual. Haz clic en 'Siguiente' para saltar de categoría.",
                         trigger_signal="clicked"),
            TutorialStep(self.nav_buttons[2], "Puedes personalizar toda la estética en Configuración. Haz clic para entrar.",
                         trigger_signal="clicked"),
            TutorialStep(self.settings_view.acrylic_btn, "Prueba a activar el efecto 'Acrylic' para ver la transparencia.",
                         trigger_signal="clicked"),
            TutorialStep(None, "¡Felicidades! Has completado el proceso de prueba. Ya estás listo para usar GDD con tus propios archivos.")
        ]
        self.tutorial.start(steps)

    def _apply_theme(self):
        """Apply theme and Windows effects with WinUI 3 standards"""
        self.setStyleSheet(get_stylesheet())
        
        if is_drawing_glass():
            # Keep translucency active
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            
            try:
                hwnd = int(self.winId())
                tm = get_theme_manager()
                is_dark = tm.theme_mode == "dark" or (tm.auto_theme and is_system_dark_mode())
                
                # IMPORTANT: Force window to update its frame logic
                WindowsEffect.set_window_dark_mode(hwnd, is_dark)
                
                # Apply based on user selection
                use_acrylic_blur = (tm.transparency_mode == "acrylic")
                WindowsEffect.apply_best_effect(hwnd, is_dark, tm.transparency_level, use_acrylic=use_acrylic_blur)
            except Exception as e:
                print(f"Transparency application error: {e}")
        else:
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        
        self.update()

# ==========================================
# ENTRY POINT
# ==========================================

def main():
    itmq_license.ensure_trial_initiated()
    
    # Attempt automatic online activation if not activated
    if not itmq_license.is_activated():
        itmq_license.check_online_activation()
        
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Splash
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "Intramaq-logo.png")
    if os.path.exists(logo_path):
        splash_pix = QPixmap(logo_path).scaled(350, 350, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        splash = QSplashScreen(splash_pix)
        splash.show()
        splash.showMessage("Cargando...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, QColor("white"))
        app.processEvents()
        
        # Build main window
        window = MainWindow()
        
        # Fade out splash
        def finish_splash():
            anim = QPropertyAnimation(splash, b"windowOpacity")
            anim.setDuration(800)
            anim.setStartValue(1.0)
            anim.setEndValue(0.0)
            anim.finished.connect(lambda: (splash.close(), window.showMaximized()))
            anim.start()
            # We keep a reference to anim so it's not GC'd
            window._splash_anim = anim

        QTimer.singleShot(1500, finish_splash)
    else:
        window = MainWindow()
        window.showMaximized()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
