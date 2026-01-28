import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import io
import os
import re
import threading
import unicodedata
import json
import time
from concurrent.futures import ThreadPoolExecutor
import sys
import stat
import subprocess
import gc
import itmq_license


# --- SINGLE INSTANCE CHECK ---
def check_single_instance():
    lock_file = os.path.join(APP_DATA_DIR, "app.lock")
    if os.path.exists(lock_file):
        try:
            # Check if process is actually running
            with open(lock_file, "r") as f:
                old_pid = int(f.read().strip())
            
            # On Windows, tasklist is reliable
            res = subprocess.run(["tasklist", "/FI", f"PID eq {old_pid}", "/FO", "CSV"], capture_output=True, text=True)
            if str(old_pid) in res.stdout:
                messagebox.showwarning("Aplicación Abierta", "El Clasificador PDF ya se está ejecutando.")
                os._exit(0)
        except:
            pass
            
    try:
        with open(lock_file, "w") as f:
            f.write(str(os.getpid()))
    except:
        pass

# --- GLOBAL SETTINGS & PERSISTENCE ---
# Use LOCALAPPDATA to avoid permission issues in Program Files or Network Drives
APP_DATA_DIR = os.path.join(os.getenv('LOCALAPPDATA', os.path.expanduser('~')), "ClasificadorPDF")
if not os.path.exists(APP_DATA_DIR):
    try:
        os.makedirs(APP_DATA_DIR)
    except OSError as e:
        print(f"Error creating app data dir: {e}")

SETTINGS_FILE = os.path.join(APP_DATA_DIR, "user_settings.json")
DEFAULT_SETTINGS = {
    "theme": "light",
    "animations": True
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return {**DEFAULT_SETTINGS, **json.load(f)}
        except Exception as e:
            print(f"Error loading settings: {e}")
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    except OSError as e:
        print(f"Error saving settings: {e}")

UI_SETTINGS = load_settings()
CURRENT_THEME = UI_SETTINGS["theme"]
ANIMATIONS_ENABLED = UI_SETTINGS["animations"]

# --- VERSION INFO ---
APP_VERSION = "1.4.23" 

def check_for_updates():
    """Checks for updates by fetching version.json from GitHub."""
    threading.Thread(target=_async_check_updates, daemon=True).start()

def _async_check_updates():
    try:
        import urllib.request
        import json
        
        # URL for the version metadata on GitHub
        url = "https://raw.githubusercontent.com/Illioners/ITMQ-DPDF-Release/main/version.json"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'ITMQ-GD-Client'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        new_version = data.get("version")
        
        def parse_version(v):
            return tuple(map(int, (v.split("."))))

        if new_version:
            try:
                if parse_version(new_version) > parse_version(APP_VERSION):
                    # We use after() to show the message box in the main thread
                    from tkinter import messagebox
                    def _ask_update():
                        if messagebox.askyesno("Actualización Disponible", 
                            f"Hay una nueva versión disponible: {new_version}\n\n"
                            f"¿Desea actualizar ahora?\n\n"
                            f"Cambios:\n{data.get('changelog', 'Mejoras generales.')}"):
                            
                            # Handle Updater Path logic for Frozen vs Dev
                            if getattr(sys, 'frozen', False):
                                # Running as compiled exe
                                base_dir = os.path.dirname(sys.executable)
                                updater_exe = os.path.join(base_dir, "ITMQ-Updater.exe")
                                
                                if os.path.exists(updater_exe):
                                    # Launch updater exe directly
                                    cmd = [
                                        updater_exe,
                                        "--target", sys.executable,
                                        "--url", data.get("download_url", ""),
                                        "--version", new_version,
                                        "--sha256", data.get("sha256", "")
                                    ]
                                    subprocess.Popen(cmd)
                                    os._exit(0)
                                else:
                                    messagebox.showerror("Error", f"No se encontró ITMQ-Updater.exe\n\nBuscado en:\n{updater_exe}\n\nPor favor, descarga la actualización manualmente.")
                            else:
                                # Running from source
                                updater_path = os.path.join(os.path.dirname(__file__), "itmq_updater.py")
                                if os.path.exists(updater_path):
                                    cmd = [
                                        sys.executable, updater_path,
                                        "--target", sys.argv[0],
                                        "--url", data.get("download_url", ""),
                                        "--version", new_version,
                                        "--sha256", data.get("sha256", "")
                                    ]
                                    subprocess.Popen(cmd)
                                    os._exit(0)
                    
                    # Since check_for_updates is called before mainloop starts in many cases,
                    # or from threads, we need to be careful with UI.
                    try:
                        _ask_update()
                    except:
                        pass
            except ValueError:
                print(f"Version parse error: {new_version} vs {APP_VERSION}")

    except Exception as e:
        print(f"Update check error: {e}")

# --- LICENSE SYSTEM UI ---
class LicenseDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Activación de Licencia")
        self.geometry("500x350")
        self.resizable(False, False)
        self.configure(bg=COLORS["BG"])
        self.transient(parent)
        self.grab_set()
        
        # Center
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (250)
        y = (self.winfo_screenheight() // 2) - (175)
        self.geometry(f"+{x}+{y}")
        
        self.success = False
        
        self.setup_ui()
        
    def setup_ui(self):
        # Header
        header = tk.Frame(self, bg=COLORS["BLUE"], height=60)
        header.pack(fill="x")
        tk.Label(header, text="Activación ITMQ-GD", font=("Segoe UI", 14, "bold"), bg=COLORS["BLUE"], fg="white").pack(pady=15)
        
        content = tk.Frame(self, bg=COLORS["BG"], padx=30, pady=20)
        content.pack(fill="both", expand=True)
        
        tk.Label(content, text="Esta aplicación requiere una licencia válida.", font=FONTS["BOLD"], bg=COLORS["BG"]).pack(anchor="w")
        tk.Label(content, text="Por favor, introduzca la Llave Maestra proporcionada por su proveedor.", 
                 font=("Segoe UI", 9), bg=COLORS["BG"], wraplength=440, justify="left").pack(anchor="w", pady=(5, 10))
        
        # Key Entry
        tk.Label(content, text="LLAVE DE ACTIVACIÓN:", font=FONTS["BOLD"], bg=COLORS["BG"]).pack(anchor="w", pady=(10, 5))
        self.key_var = tk.StringVar()
        self.entry_key = tk.Entry(content, textvariable=self.key_var, font=("Consolas", 12), bd=1, relief="solid")
        self.entry_key.pack(fill="x", pady=5)
        self.entry_key.focus_set()
        
        # Action Buttons
        btn_frame = tk.Frame(content, bg=COLORS["BG"])
        btn_frame.pack(fill="x", pady=20)
        
        self.btn_activate = tk.Button(btn_frame, text="ACTIVAR AHORA", command=self.activate, 
                                     bg=COLORS["BLUE"], fg="white", font=FONTS["BOLD"], padx=20, pady=8, bd=0, cursor="hand2")
        self.btn_activate.pack(side="right")
        
        tk.Button(btn_frame, text="Salir", command=lambda: os._exit(0), bg=COLORS["BG"], bd=0, cursor="hand2").pack(side="left")

    def activate(self):
        key = self.key_var.get().strip()
        dtype = itmq_license.validate_key(key)
        if dtype:
            if itmq_license.save_license(key, dtype):
                messagebox.showinfo("Éxito", f"¡Aplicación activada correctamente!\nTipo: {dtype}")
                self.success = True
                self.destroy()
            else:
                messagebox.showerror("Error", "No se pudo guardar el archivo de licencia.")
        else:
            messagebox.showerror("Error", "La llave de activación no es válida.")

# --- DOCUMENT TYPE SELECTION DIALOG ---
class DocumentTypeDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Seleccionar Tipo de Documento")
        self.resizable(False, False)
        self.configure(bg=COLORS["BG"])
        self.transient(parent)
        self.grab_set()
        
        self.selected_types = []  # Changed to list for multiple selections
        
        # Track selection state
        self.selections = {
            "Ingreso": False,
            "En Curso": False,
            "Retiro": False
        }
        
        self.setup_ui()
        
        # Auto-adjust size and center after UI is built
        self.update_idletasks()
        width = 550  # Fixed width for better layout
        height = self.winfo_reqheight()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
    def setup_ui(self):
        # Header with gradient effect
        header = tk.Frame(self, bg=COLORS["BLUE"], height=100)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(header, text="📄", font=("Segoe UI", 32), 
                bg=COLORS["BLUE"], fg="white").pack(pady=(15, 0))
        tk.Label(header, text="Tipo de Documento", 
                font=("Segoe UI Variable Display", 20, "bold"), 
                bg=COLORS["BLUE"], fg="white").pack(pady=(5, 15))
        
        # Content
        content = tk.Frame(self, bg=COLORS["BG"], padx=30, pady=30)
        content.pack(fill="both", expand=True)
        
        tk.Label(content, text="Seleccione uno o más tipos de documento:", 
                font=("Segoe UI Variable Text", 11), bg=COLORS["BG"], 
                fg=COLORS["TEXT"]).pack(anchor="w", pady=(0, 20))
        
        # Cards container
        cards_container = tk.Frame(content, bg=COLORS["BG"])
        cards_container.pack(fill="both", expand=True, pady=10)
        
        # Create interactive cards for each document type
        self.cards = {}
        
        # Ingreso Card
        self.cards["Ingreso"] = self._create_card(
            cards_container, 
            "Ingreso",
            "📥",
            COLORS.get("CAT_INGRESO", COLORS["GREEN"]),
            "Documentos de ingreso de personal"
        )
        self.cards["Ingreso"].pack(fill="x", pady=8)
        
        # En Curso Card
        self.cards["En Curso"] = self._create_card(
            cards_container,
            "En Curso",
            "📋",
            COLORS.get("CAT_ENCURSO", COLORS["BLUE"]),
            "Documentos en proceso activo"
        )
        self.cards["En Curso"].pack(fill="x", pady=8)
        
        # Retiro Card
        self.cards["Retiro"] = self._create_card(
            cards_container,
            "Retiro",
            "📤",
            COLORS.get("CAT_RETIRO", COLORS["RED"]),
            "Documentos de retiro/salida"
        )
        self.cards["Retiro"].pack(fill="x", pady=8)
        
        # Action buttons
        btn_frame = tk.Frame(content, bg=COLORS["BG"])
        btn_frame.pack(pady=(30, 0), fill="x")
        
        tk.Button(btn_frame, text="Cancelar", command=self.destroy,
                 bg=COLORS["ACCENT"], fg=COLORS["TEXT"], 
                 font=("Segoe UI Variable Text", 10),
                 padx=20, pady=10, bd=0, cursor="hand2",
                 relief="flat").pack(side="left")
        
        RoundedButton(btn_frame, "CONFIRMAR ✓", command=self.confirm_selection, 
                     width=180, height=50, gradient=True).pack(side="right")
    
    def _create_card(self, parent, doc_type, icon, color, description):
        """Create an interactive card for document type selection"""
        # Card frame with hover effect
        card_frame = tk.Frame(parent, bg=COLORS["SURFACE"], bd=0,
                             highlightthickness=2, highlightbackground=COLORS["BORDER"])
        
        # Inner container for padding
        inner = tk.Frame(card_frame, bg=COLORS["SURFACE"])
        inner.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Left side: Icon
        left_frame = tk.Frame(inner, bg=COLORS["SURFACE"])
        left_frame.pack(side="left", padx=(0, 15))
        
        icon_label = tk.Label(left_frame, text=icon, font=("Segoe UI", 36),
                             bg=COLORS["SURFACE"], fg=color)
        icon_label.pack()
        
        # Right side: Text content
        right_frame = tk.Frame(inner, bg=COLORS["SURFACE"])
        right_frame.pack(side="left", fill="both", expand=True)
        
        title_label = tk.Label(right_frame, text=doc_type.upper(),
                              font=("Segoe UI Variable Display", 14, "bold"),
                              bg=COLORS["SURFACE"], fg=color, anchor="w")
        title_label.pack(fill="x")
        
        desc_label = tk.Label(right_frame, text=description,
                             font=("Segoe UI Variable Text", 9),
                             bg=COLORS["SURFACE"], fg=COLORS["TEXT_SECONDARY"],
                             anchor="w")
        desc_label.pack(fill="x", pady=(2, 0))
        
        # Selection indicator (checkmark)
        check_frame = tk.Frame(inner, bg=COLORS["SURFACE"], width=40)
        check_frame.pack(side="right")
        check_frame.pack_propagate(False)
        
        check_label = tk.Label(check_frame, text="", font=("Segoe UI", 20),
                              bg=COLORS["SURFACE"], fg=color)
        check_label.pack(expand=True)
        
        # Store references for updates
        card_frame._inner = inner
        card_frame._icon_label = icon_label
        card_frame._title_label = title_label
        card_frame._desc_label = desc_label
        card_frame._check_label = check_label
        card_frame._color = color
        card_frame._doc_type = doc_type
        
        # Bind click events to all components
        for widget in [card_frame, inner, left_frame, right_frame, icon_label, 
                      title_label, desc_label, check_frame, check_label]:
            widget.bind("<Button-1>", lambda e, dt=doc_type: self._toggle_selection(dt))
            widget.bind("<Enter>", lambda e, cf=card_frame: self._on_card_hover(cf, True))
            widget.bind("<Leave>", lambda e, cf=card_frame: self._on_card_hover(cf, False))
            widget.config(cursor="hand2")
        
        return card_frame
    
    def _toggle_selection(self, doc_type):
        """Toggle selection state for a document type"""
        self.selections[doc_type] = not self.selections[doc_type]
        self._update_card_appearance(doc_type)
    
    def _update_card_appearance(self, doc_type):
        """Update card visual state based on selection"""
        card = self.cards[doc_type]
        is_selected = self.selections[doc_type]
        color = card._color
        
        if is_selected:
            # Selected state - vibrant colors
            card.config(highlightbackground=color, highlightthickness=3)
            card._inner.config(bg=COLORS.get("BLUE_LIGHT", COLORS["SURFACE"]))
            card._icon_label.config(bg=COLORS.get("BLUE_LIGHT", COLORS["SURFACE"]))
            card._title_label.config(bg=COLORS.get("BLUE_LIGHT", COLORS["SURFACE"]))
            card._desc_label.config(bg=COLORS.get("BLUE_LIGHT", COLORS["SURFACE"]))
            card._check_label.config(text="✓", bg=COLORS.get("BLUE_LIGHT", COLORS["SURFACE"]))
        else:
            # Unselected state
            card.config(highlightbackground=COLORS["BORDER"], highlightthickness=2)
            card._inner.config(bg=COLORS["SURFACE"])
            card._icon_label.config(bg=COLORS["SURFACE"])
            card._title_label.config(bg=COLORS["SURFACE"])
            card._desc_label.config(bg=COLORS["SURFACE"])
            card._check_label.config(text="", bg=COLORS["SURFACE"])
    
    def _on_card_hover(self, card, entering):
        """Handle hover effects on cards"""
        if entering and not self.selections[card._doc_type]:
            card.config(highlightbackground=card._color, highlightthickness=2)
        elif not entering and not self.selections[card._doc_type]:
            card.config(highlightbackground=COLORS["BORDER"], highlightthickness=2)
    
    def confirm_selection(self):
        # Collect selected types
        selected = [doc_type for doc_type, is_selected in self.selections.items() if is_selected]
        
        if not selected:
            messagebox.showwarning("Selección Requerida", 
                                  "Por favor seleccione al menos un tipo de documento.")
            return
        
        self.selected_types = selected
        self.destroy()


# --- CONFIGURATION & STYLING ---
THEMES = {
    "light": {
        # Primary Colors
        "BLUE": "#FF6B35",  # Vibrant Orange (Primary Action)
        "BLUE_HOVER": "#E85D2F",  # Darker Orange on Hover
        "BLUE_LIGHT": "#FFE8DF",  # Very Light Orange Background
        "RED": "#E63946",  # Vibrant Red
        "GREEN": "#06D6A0",  # Vibrant Teal Green
        "PURPLE": "#7209B7",  # Vibrant Purple
        "YELLOW": "#FFB703",  # Vibrant Yellow
        
        # Backgrounds
        "BG": "#F8F9FA",  # Light Gray Background
        "SURFACE": "#FFFFFF",  # Pure White Surface
        "SURFACE_HOVER": "#F1F3F5",  # Light Hover State
        
        # Text
        "TEXT": "#212529",  # Almost Black
        "TEXT_SECONDARY": "#6C757D",  # Medium Gray
        "TEXT_TERTIARY": "#ADB5BD",  # Light Gray
        
        # Borders & Accents
        "BORDER": "#DEE2E6",  # Light Border
        "BORDER_FOCUS": "#FF6B35",  # Orange Border on Focus
        "ACCENT": "#E9ECEF",  # Light Accent
        
        # Shadows & Effects (solid colors, no alpha)
        "SHADOW_LIGHT": "#F0F0F0",  # Very Light Gray Shadow
        "SHADOW_MEDIUM": "#E0E0E0",  # Medium Gray Shadow
        "SHADOW_DARK": "#D0D0D0",  # Darker Gray Shadow
        
        # Category Colors
        "CAT_INGRESO": "#06D6A0",  # Teal for Ingreso
        "CAT_ENCURSO": "#118AB2",  # Blue for En Curso
        "CAT_RETIRO": "#EF476F",  # Pink-Red for Retiro
        
        # Status Colors
        "SUCCESS": "#06D6A0",
        "WARNING": "#FFB703",
        "ERROR": "#E63946",
        "INFO": "#118AB2"
    },
    "dark": {
        # Primary Colors
        "BLUE": "#FF6B35",  # Vibrant Orange
        "BLUE_HOVER": "#FF8555",  # Lighter Orange on Hover (inverted for dark)
        "BLUE_LIGHT": "#2A2A2A",  # Dark Surface
        "RED": "#FF6B6B",  # Softer Red for Dark Mode
        "GREEN": "#51CF66",  # Softer Green
        "PURPLE": "#9775FA",  # Softer Purple
        "YELLOW": "#FFD43B",  # Softer Yellow
        
        # Backgrounds
        "BG": "#121212",  # True Dark Background
        "SURFACE": "#1E1E1E",  # Dark Surface
        "SURFACE_HOVER": "#2A2A2A",  # Lighter on Hover
        
        # Text
        "TEXT": "#E9ECEF",  # Light Gray Text
        "TEXT_SECONDARY": "#ADB5BD",  # Medium Gray
        "TEXT_TERTIARY": "#6C757D",  # Darker Gray
        
        # Borders & Accents
        "BORDER": "#343A40",  # Dark Border
        "BORDER_FOCUS": "#FF6B35",  # Orange Border on Focus
        "ACCENT": "#2C3034",  # Dark Accent
        
        # Shadows & Effects (solid colors, no alpha)
        "SHADOW_LIGHT": "#2A2A2A",  # Light Shadow
        "SHADOW_MEDIUM": "#252525",  # Medium Shadow
        "SHADOW_DARK": "#202020",  # Dark Shadow
        
        # Category Colors (Slightly muted for dark mode)
        "CAT_INGRESO": "#51CF66",  # Softer Teal
        "CAT_ENCURSO": "#4DABF7",  # Softer Blue
        "CAT_RETIRO": "#FF6B6B",  # Softer Pink-Red
        
        # Status Colors
        "SUCCESS": "#51CF66",
        "WARNING": "#FFD43B",
        "ERROR": "#FF6B6B",
        "INFO": "#4DABF7"
    }
}

COLORS = THEMES[CURRENT_THEME]

FONTS = {
    "MAIN": ("Segoe UI Variable Text", 10),
    "BOLD": ("Segoe UI Variable Text", 10, "bold"),
    "TITLE": ("Segoe UI Variable Display", 22, "bold"),
    "SUBTITLE": ("Segoe UI Variable Text", 11),
}
# Fallback font handling will be done in main() after root initialization

# --- PROFILES & CATEGORIES ---
PROFILES = {
    "Gestion Humana": {
        "CATEGORIES": [
            # A. Contrato (Imagen 1)
            ("CC", "Cédula de ciudadanía"),
            ("RQ", "Requisición"),
            ("HVI", "Hoja de Vida Interna"),
            ("HVE", "Hoja de Vida Externa"),
            ("CTO", "Contrato"),
            ("CTOF", "Contrato Firmado"),
            ("NR", "No Renovación/No Prorroga"),
            ("PC", "Perfil del Cargo"),
            ("ATD", "Autorización de Datos"),
            ("ES", "Exclusión Salarial"),
            ("DOCB", "Documentos de Beneficiarios"),
            ("NOIB", "No Inclusión de Beneficiarios"),
            ("LC", "Licencia de Conducción"),
            ("CV", "Carnet de Vacunación"),
            ("ANT", "Antecedentes"),
            ("EI", "Entrevista de Ingreso"),
            ("APL", "Aceptación de la Propuesta Laboral"),
            ("PV", "Póliza de Vida (documento de asegurabilidad)"),
            ("PSD", "Perfil Socio Demográfico"),
            ("GEO", "Geovictoria"),
            
            # B. Afiliaciones (Imagen 2)
            ("ARL", "Certificado de Administradora de Riesgos Laborales"),
            ("FEPS", "Formulario de Entidad Promotora de Salud"),
            ("EPS", "Certificado de Entidad Promotora de Salud"),
            ("AFP", "Certificado Administradora de Fondos de Pensiones"),
            ("FCCF", "Formulario de Caja de Compensación Familiar"),
            ("CCF", "Certificado Caja de Compensación Familiar"),
            ("ADRES", "Administradora de recursos SGSSS"),
            ("RUAF", "Registro Único de Afiliados en Colombia"),
            
            # C. Certificaciones (Imagen 3)
            ("CB", "Certificado Bancario"),
            ("CE", "Certificado de Estudio"),
            ("CL", "Certificado Laboral"),
            ("CF", "Certificado de la funeraria"),
            
            # D. Documentos adicionales
            ("DOC", "Documentos Adicionales")
        ],
        "SEGMENTS": {
            "A. Contrato": ["CC", "RQ", "HVI", "HVE", "CTO", "CTOF", "NR", "PC", "ATD", "ES", "DOCB", "NOIB", "LC", "CV", "ANT", "EI", "APL", "PV", "PSD", "GEO"],
            "B. Afiliaciones": ["ARL", "FEPS", "EPS", "AFP", "FCCF", "CCF", "ADRES", "RUAF"],
            "C. Certificaciones": ["CB", "CE", "CL", "CF"],
            "D. Documentos adicionales": ["DOC"]
        }
    },
    "En Curso": {
        "CATEGORIES": [
            ("PD", "Procesos Disciplinarios"),
            ("TJ", "Tarjetas"),
            ("ED", "Evaluación Desempeño"),
            ("PM", "Permiso"),
            ("VA", "Vacaciones"),
            ("CCO", "Circulares Colectivas"),
            ("ADTO", "Autorizaciones de Descuento"),
            ("SI", "Solicitud Cesantías"),
            ("IN", "Incapacidades")
        ],
        "SEGMENTS": {
            "Documentos En Curso": ["PD", "TJ", "ED", "PM", "VA", "CCO", "ADTO", "SI", "IN"]
        }
    },
    "Retiro": {
        "CATEGORIES": [
            ("LQ", "Liquidación"),
            ("PZS", "Paz y Salvo"),
            ("CLA", "Cert Laboral"),
            ("CCE", "Cert Cesantías"),
            ("CSO", "Cert Aportes Seguridad Social"),
            ("RSA", "Renuncia SA"),
            ("ASA", "Aceptación SA"),
            ("ACO", "Aut Exámenes Médicos/Term Contrato")
        ],
        "SEGMENTS": {
            "Documentos Retiro": ["LQ", "PZS", "CLA", "CCE", "CSO", "RSA", "ASA", "ACO"]
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

# --- PDF ENGINE ---
class PDFEngine:
    _executor = ThreadPoolExecutor(max_workers=os.cpu_count())

    def __init__(self, file_path):
        self.file_path = file_path
        self.doc = fitz.open(file_path)
        self.cache = {}
        self.cache_keys = []
        self.MAX_CACHE = 20 # Optimized for low-end systems
        self.ocr_cache = {}
        self.rotations = {}
        self.id_regex = re.compile(r'\d{7,10}')
        self._lock = threading.Lock()

    def get_page_preview(self, page_num, scale=0.3):
        rot = self.rotations.get(page_num, 0)
        key = (page_num, scale, rot)
        
        with self._lock:
            if key in self.cache:
                if key in self.cache_keys:
                    self.cache_keys.remove(key)
                self.cache_keys.append(key)
                return self.cache[key]
        
        try:
            page = self.doc.load_page(page_num)
            matrix = fitz.Matrix(scale, scale).prerotate(rot)
            # Use alpha=False for faster rendering if not needed
            pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        except Exception as e:
            print(f"Render error p{page_num}: {e}")
            return None
        
        with self._lock:
            self.cache[key] = img
            self.cache_keys.append(key)
            if len(self.cache_keys) > self.MAX_CACHE:
                oldest = self.cache_keys.pop(0)
                self.cache.pop(oldest, None)
            
        return img

    def prefetch(self, page_nums, scale=0.25):
        """Pre-renders a list of pages in the background."""
        def _target():
            for p in page_nums:
                if p < 0 or p >= self.doc.page_count: continue
                self.get_page_preview(p, scale)
        self._executor.submit(_target)

    def async_render(self, page_num, scale, callback):
        def _task():
            img = self.get_page_preview(page_num, scale)
            if img: callback(img)
        self._executor.submit(_task)

    def rotate_page(self, page_num):
        curr = self.rotations.get(page_num, 0)
        self.rotations[page_num] = (curr - 90) % 360
        # Clear specific cache
        ks = [k for k in self.cache if k[0] == page_num]
        for k in ks: del self.cache[k]
        return self.rotations[page_num]

    def get_text_clean(self, page_num):
        if page_num in self.ocr_cache: return self.ocr_cache[page_num]
        try:
            page = self.doc.load_page(page_num)
            text = page.get_text()
        except Exception as e:
            print(f"Text extraction error p{page_num}: {e}")
            text = ""
        
        clean = ''.join((c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')).lower()
        self.ocr_cache[page_num] = clean
        return clean

    def close(self):
        self.doc.close()

# --- CUSTOM WIDGETS ---
class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command=None, width=200, height=45, color=None, fg_color="white", icon=None, gradient=False, **kwargs):
        self.color = color or COLORS["BLUE"]
        self.fg_color = fg_color or "white"
        self.icon = icon
        self.gradient = gradient
        
        super().__init__(parent, width=width, height=height, bg=parent["bg"], highlightthickness=0, cursor="hand2")
        self.command = command
        self.text = text
        self.state = "normal"
        self.hover_state = False
        self.draw()
        
        self.bind("<Button-1>", lambda e: self._on_click())
        self.bind("<Enter>", lambda e: self._on_enter())
        self.bind("<Leave>", lambda e: self._on_leave())

    def _on_enter(self):
        self.hover_state = True
        self.draw(hover=True)
    
    def _on_leave(self):
        self.hover_state = False
        self.draw(hover=False)

    def draw(self, hover=False):
        self.delete("all")
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        
        if self.state == "disabled":
            c = COLORS["BORDER"]
            shadow_c = COLORS.get("SHADOW_LIGHT", "#F0F0F0")
        else:
            c = COLORS.get("BLUE_HOVER", self.color) if hover else self.color
            # Use same shadow color, just slightly different intensity
            shadow_c = COLORS.get("SHADOW_MEDIUM", "#E0E0E0") if hover else COLORS.get("SHADOW_LIGHT", "#F0F0F0")
        
        # Draw shadow with FIXED offset to prevent jitter
        shadow_offset = 3  # Fixed offset
        if self.state != "disabled":
            # Single shadow layer for better performance
            self._draw_rounded_rect(
                3, 3 + shadow_offset, 
                w - 3, h - 3 + shadow_offset, 
                12, fill=shadow_c, outline=""
            )
        
        # Draw main button with gradient effect
        if self.gradient and self.state != "disabled":
            # Simulate gradient with multiple rectangles
            steps = 8  # Reduced from 10 for better performance
            for i in range(steps):
                y_start = 3 + (h - 6) * i / steps
                y_end = 3 + (h - 6) * (i + 1) / steps
                
                # Calculate color interpolation
                ratio = i / steps
                if hover:
                    # Lighter gradient on hover
                    shade = self._lighten_color(c, 0.1 * (1 - ratio))
                else:
                    shade = self._darken_color(c, 0.05 * ratio)
                
                self.create_rectangle(
                    3, y_start, w - 3, y_end,
                    fill=shade, outline=""
                )
            # Add rounded corners on top
            self._draw_rounded_rect(3, 3, w-3, h-3, 12, fill="", outline=c, width=0)
        else:
            # Solid color button
            self._draw_rounded_rect(3, 3, w-3, h-3, 12, fill=c, outline="")
        
        # Add subtle inner highlight (top edge) - only when not hovering
        if self.state != "disabled" and not hover:
            highlight = self._lighten_color(c, 0.15)
            self.create_line(15, 5, w-15, 5, fill=highlight, width=1, smooth=True)
        
        # Draw text with icon if provided
        text_x = w / 2
        if self.icon:
            icon_x = w / 2 - 30
            self.create_text(icon_x, h / 2, text=self.icon, 
                           fill=self.fg_color if self.state != "disabled" else COLORS["TEXT_SECONDARY"], 
                           font=("Segoe UI", 14))
            text_x = w / 2 + 10
        
        self.create_text(text_x, h / 2, text=self.text, 
                        fill=self.fg_color if self.state != "disabled" else COLORS["TEXT_SECONDARY"], 
                        font=FONTS["BOLD"])

    def _lighten_color(self, hex_color, factor):
        """Lighten a hex color by a factor (0-1)"""
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            r = min(255, int(r + (255 - r) * factor))
            g = min(255, int(g + (255 - g) * factor))
            b = min(255, int(b + (255 - b) * factor))
            return f'#{r:02x}{g:02x}{b:02x}'
        except:
            return hex_color
    
    def _darken_color(self, hex_color, factor):
        """Darken a hex color by a factor (0-1)"""
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            r = max(0, int(r * (1 - factor)))
            g = max(0, int(g * (1 - factor)))
            b = max(0, int(b * (1 - factor)))
            return f'#{r:02x}{g:02x}{b:02x}'
        except:
            return hex_color

    def _on_click(self):
        if self.state == "normal" and self.command: 
            # Visual feedback on click
            self.draw(hover=False)
            self.after(100, lambda: self.draw(hover=self.hover_state))
            self.command()

    def set_text(self, new_text):
        self.text = new_text
        self.draw()

    def set_state(self, state):
        self.state = state
        self.draw()

    def refresh_theme(self, color=None):
        if color: self.color = color
        self.config(bg=self.master["bg"])
        self.draw()

    def _draw_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1+r, y1, x2-r, y1, x2, y1, x2, y1+r, 
            x2, y2-r, x2, y2, x2-r, y2, x1+r, y2, 
            x1, y2, x1, y2-r, x1, y1+r, x1, y1
        ]
        return self.create_polygon(points, **kwargs, smooth=True)


class Tooltip:
    """A simple tooltip class for Tkinter widgets."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text: return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        # Use current theme colors
        bg_color = COLORS.get("SURFACE", "#2c3e50")
        fg_color = COLORS.get("TEXT", "#ecf0f1")
        
        label = tk.Label(tw, text=self.text, justify='left',
                         background=bg_color, foreground=fg_color,
                         relief='solid', borderwidth=1,
                         font=("Segoe UI Variable Text", 9),
                         padx=8, pady=4)
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw: tw.destroy()

class HighResCanvas(tk.Frame):
    def __init__(self, parent, page_obj, page_num=None, engine=None):
        super().__init__(parent, bg=COLORS["BG"])
        self.page_obj = page_obj
        self.page_num = page_num
        self.engine = engine
        self.zoom_level = 2.0
        self._resize_job = None  # For debouncing resize events
        
        self.canvas = tk.Canvas(self, bg=COLORS["BG"], highlightthickness=0)
        self.v_scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.h_scroll = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        
        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll.pack(side="bottom", fill="x")
        self.canvas.pack(fill="both", expand=True)

        self.tk_img = None
        
        # Wait for widget to be fully sized before rendering
        self.after(100, self.render_image)

        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Control-MouseWheel>", self._on_zoom)
        # Bind to parent too for better coverage
        self.bind("<MouseWheel>", self._on_mousewheel)
        
        # Bind to resize event for auto-adjustment
        self.canvas.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        """Handle canvas resize with debouncing to avoid excessive re-renders"""
        # Cancel pending resize job if exists
        if self._resize_job:
            self.after_cancel(self._resize_job)
        
        # Schedule new resize job after 200ms of no resize events
        self._resize_job = self.after(200, self._handle_resize)
    
    def _handle_resize(self):
        """Actually handle the resize after debouncing"""
        self._resize_job = None
        if self.tk_img:  # Only re-center if image exists
            self._recenter_image()

    def _recenter_image(self):
        """Recenter the existing image without re-rendering"""
        if not self.tk_img:
            return
            
        # Get current canvas size
        self.canvas.update_idletasks()
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        
        # Get image dimensions
        img_w = self.tk_img.width()
        img_h = self.tk_img.height()
        
        # Calculate centered position
        x_pos = max(0, (cw - img_w) // 2)
        y_pos = max(0, (ch - img_h) // 2)
        
        # Redraw image at new position
        self.canvas.delete("all")
        self.canvas.create_image(x_pos, y_pos, image=self.tk_img, anchor="nw")
        
        # Update scroll region
        self.canvas.config(scrollregion=(0, 0, max(cw, img_w), max(ch, img_h)))
        
        # Center the scroll if image is larger than canvas
        if img_w > cw or img_h > ch:
            x_scroll = (img_w - cw) / (2 * img_w) if img_w > cw else 0
            y_scroll = (img_h - ch) / (2 * img_h) if img_h > ch else 0
            self.canvas.xview_moveto(x_scroll)
            self.canvas.yview_moveto(y_scroll)

    def render_image(self):
        rot = 0
        if self.engine and self.page_num is not None:
            rot = self.engine.rotations.get(self.page_num, 0)
            
        matrix = fitz.Matrix(self.zoom_level, self.zoom_level).prerotate(rot)
        pix = self.page_obj.get_pixmap(matrix=matrix)
        img_pil = Image.open(io.BytesIO(pix.tobytes()))
        self.tk_img = ImageTk.PhotoImage(img_pil) 
        
        # Get actual canvas size
        self.canvas.update_idletasks()
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        
        # Calculate centered position
        img_w = self.tk_img.width()
        img_h = self.tk_img.height()
        
        x_pos = max(0, (cw - img_w) // 2)
        y_pos = max(0, (ch - img_h) // 2)
        
        self.canvas.delete("all")
        self.canvas.create_image(x_pos, y_pos, image=self.tk_img, anchor="nw")
        
        # Set scroll region to include the entire image
        self.canvas.config(scrollregion=(0, 0, max(cw, img_w), max(ch, img_h)))
        
        # Center the view if image is larger than canvas
        if img_w > cw or img_h > ch:
            # Calculate scroll position to center the image
            x_scroll = (img_w - cw) / (2 * img_w) if img_w > cw else 0
            y_scroll = (img_h - ch) / (2 * img_h) if img_h > ch else 0
            self.canvas.xview_moveto(x_scroll)
            self.canvas.yview_moveto(y_scroll)

    def _on_zoom(self, event):
        if event.delta > 0: self.zoom_level *= 1.2
        else: self.zoom_level /= 1.2
        self.zoom_level = max(0.5, min(5.0, self.zoom_level))
        self.render_image()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def refresh_theme(self):
        self.config(bg=COLORS["BG"])
        self.canvas.config(bg=COLORS["BG"])
        self.render_image()

    def _on_zoom_manual(self, factor):
        """Manual zoom adjustment."""
        self.zoom_level *= factor
        self.zoom_level = max(0.1, min(5.0, self.zoom_level))
        self.render_image()

class PageTile(tk.Frame):
    def __init__(self, parent, page_num, engine, on_click, on_zoom, on_rotate):
        super().__init__(parent, bg=COLORS["BG"], bd=0, highlightthickness=0)
        self.page_num = page_num
        self.engine = engine
        self.on_click = on_click
        self.on_zoom = on_zoom
        self.on_rotate = on_rotate
        self.selected = False
        self.is_rendered = False
        self.last_render_scale = 0
        self.hover = False
        
        # Main card container with rounded corners effect
        self.card = tk.Frame(self, bg=COLORS["SURFACE"], bd=0, 
                            highlightthickness=3, highlightbackground=COLORS["BORDER"])
        self.card.pack(padx=4, pady=4, fill="both", expand=True)
        
        # Image container with padding
        self.img_container = tk.Frame(self.card, bg=COLORS["SURFACE"], width=170, height=220)
        self.img_container.pack_propagate(False)
        self.img_container.pack(padx=10, pady=10)
        
        self.tk_img = None
        self.lbl_img = tk.Label(self.img_container, text="⏳", 
                               font=("Segoe UI Variable Text", 24), 
                               bg=COLORS["SURFACE"], fg=COLORS["TEXT_TERTIARY"], 
                               cursor="hand2")
        self.lbl_img.pack(expand=True, fill="both")
        
        # Bottom bar with modern design
        self.bottom_bar = tk.Frame(self.card, bg=COLORS["SURFACE"], height=40)
        self.bottom_bar.pack(fill="x", side="bottom")
        self.bottom_bar.pack_propagate(False)
        
        # Page number badge (modern circular badge)
        self.badge_frame = tk.Frame(self.bottom_bar, bg=COLORS["SURFACE"])
        self.badge_frame.pack(side="left", padx=10, pady=5)
        
        self.badge_canvas = tk.Canvas(self.badge_frame, width=32, height=32, 
                                     bg=COLORS["SURFACE"], highlightthickness=0)
        self.badge_canvas.pack()
        
        # Draw circular badge
        self._draw_badge(page_num + 1)
        
        # Rotate button with icon
        self.btn_rot = tk.Label(self.bottom_bar, text="↻", 
                               bg=COLORS["SURFACE"], fg=COLORS["BLUE"], 
                               font=("Segoe UI Variable Text", 16, "bold"), 
                               cursor="hand2", padx=8)
        self.btn_rot.pack(side="right", padx=10, pady=5)
        self.btn_rot.bind("<Button-1>", self._handle_rotate)
        
        # Hover effect for rotate button
        self.btn_rot.bind("<Enter>", lambda e: self.btn_rot.config(fg=COLORS["BLUE_HOVER"]))
        self.btn_rot.bind("<Leave>", lambda e: self.btn_rot.config(
            fg="white" if self.selected else COLORS["BLUE"]))

        # Bind events to all components
        for w in [self, self.card, self.lbl_img, self.img_container, self.bottom_bar, self.badge_frame]:
            w.bind("<Button-1>", self._handle_click)
            w.bind("<Button-3>", self._handle_right_press)
            w.bind("<ButtonRelease-3>", self._handle_right_release)
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

        if ANIMATIONS_ENABLED:
            # Set initial "invisible" state for animation
            self.lbl_img.config(fg=COLORS["BG"])
            self.bottom_bar.pack_forget()
    
    def _draw_badge(self, page_num):
        """Draw a modern circular badge with page number"""
        self.badge_canvas.delete("all")
        
        # Badge circle
        badge_color = COLORS["BLUE"] if self.selected else COLORS["ACCENT"]
        text_color = "white" if self.selected else COLORS["TEXT_SECONDARY"]
        
        # Draw circle
        self.badge_canvas.create_oval(2, 2, 30, 30, fill=badge_color, outline="", width=0)
        
        # Add subtle border
        if not self.selected:
            self.badge_canvas.create_oval(2, 2, 30, 30, fill="", 
                                         outline=COLORS["BORDER"], width=2)
        
        # Page number text
        self.badge_canvas.create_text(16, 16, text=str(page_num), 
                                     fill=text_color, 
                                     font=("Segoe UI Variable Display", 10, "bold"))

    def _handle_right_press(self, e):
        self._right_click_time = time.time()
        # Don't show zoom immediately, wait to see if it's a hold
        self._zoom_job = self.after(300, lambda: self.on_zoom(self.page_num, mode="press"))

    def _handle_right_release(self, e):
        # Cancel the pending zoom job if it hasn't fired yet
        if hasattr(self, "_zoom_job"):
            self.after_cancel(self._zoom_job)
            del self._zoom_job
            
        duration = time.time() - getattr(self, "_right_click_time", 0)
        if duration < 0.3:
            # Short click -> menu
            self.show_context_menu(e)
        else:
            # Release after hold -> close zoom if it was a hold zoom
            self.on_zoom(self.page_num, mode="release", duration=duration)

    def trigger_render(self, scale=0.25):
        if self.is_rendered and abs(self.last_render_scale - scale) < 0.05: return
        self.is_rendered = True
        self.last_render_scale = scale
        self.engine.async_render(self.page_num, scale, self._apply_image)

    def unload_image(self):
        """Free memory by unloading the PhotoImage."""
        if not self.is_rendered: return
        self.is_rendered = False
        self.tk_img = None
        self.lbl_img.config(image="", text="⏳")

    def _apply_image(self, img_pil):
        def _update():
            if not self.winfo_exists(): return
            self.tk_img = ImageTk.PhotoImage(img_pil)
            self.lbl_img.config(image=self.tk_img, text="")
        self.after(0, _update)

    def _handle_click(self, e):
        self.on_click(self, shift=(e.state & 0x0001))

    def _handle_rotate(self, e):
        self.is_rendered = False
        self.lbl_img.config(image="", text="⏳")
        self.on_rotate(self)
        self.trigger_render()

    def refresh_image(self, new_pil):
        self.tk_img = ImageTk.PhotoImage(new_pil)
        self.lbl_img.config(image=self.tk_img)

    def _on_enter(self, e):
        self.hover = True
        if not self.selected:
            # Keep same thickness, just change color
            self.card.config(highlightbackground=COLORS["BLUE"])
            # Add subtle background change for lift effect
            self.config(bg=COLORS.get("SURFACE_HOVER", COLORS["BG"]))

    def _on_leave(self, e):
        self.hover = False
        if not self.selected:
            self.card.config(highlightbackground=COLORS["BORDER"])
            self.config(bg=COLORS["BG"])

    def refresh_theme(self):
        # Update all colors based on current theme
        if self.selected:
            # Selected state with modern colors
            self.config(bg=COLORS["BG"])
            self.card.config(bg=COLORS["BLUE"], highlightbackground=COLORS["BLUE"], highlightthickness=3)
            self.img_container.config(bg=COLORS["BLUE"])
            self.lbl_img.config(bg=COLORS["BLUE"])
            self.bottom_bar.config(bg=COLORS["BLUE"])
            self.badge_frame.config(bg=COLORS["BLUE"])
            self.badge_canvas.config(bg=COLORS["BLUE"])
            self.btn_rot.config(bg=COLORS["BLUE"], fg="white")
            self._draw_badge(self.page_num + 1)
        else:
            # Not selected - use default theme colors
            self.config(bg=COLORS["BG"])
            self.card.config(bg=COLORS["SURFACE"], highlightbackground=COLORS["BORDER"], highlightthickness=3)
            self.img_container.config(bg=COLORS["SURFACE"])
            self.lbl_img.config(bg=COLORS["SURFACE"], fg=COLORS["TEXT_TERTIARY"])
            self.bottom_bar.config(bg=COLORS["SURFACE"])
            self.badge_frame.config(bg=COLORS["SURFACE"])
            self.badge_canvas.config(bg=COLORS["SURFACE"])
            self.btn_rot.config(bg=COLORS["SURFACE"], fg=COLORS["BLUE"])
            self._draw_badge(self.page_num + 1)

    def set_focus(self, focused):
        """Sets a secondary highlight for keyboard focus."""
        if focused:
            # Use a different visual indicator for focus (e.g., double border effect)
            self.card.config(highlightbackground=COLORS["BLUE"], highlightthickness=4)
        else:
            # Return to normal thickness
            self.card.config(highlightbackground=COLORS["BLUE"] if self.selected else COLORS["BORDER"], 
                           highlightthickness=3)

    def set_state(self, selected, label_text=None, color=None):
        self.selected = selected
        fill_color = color if (selected and color) else COLORS["BLUE"] if selected else COLORS["SURFACE"]
        
        # Update outer frame
        self.config(bg=COLORS["BG"])
        
        # Update card - FIXED thickness to prevent clipping
        self.card.config(bg=fill_color, 
                        highlightbackground=fill_color if selected else COLORS["BORDER"],
                        highlightthickness=3)  # Fixed at 3 always
        
        # Update image container
        self.img_container.config(bg=fill_color)
        self.lbl_img.config(bg=fill_color)
        
        # Update bottom bar
        self.bottom_bar.config(bg=fill_color)
        self.badge_frame.config(bg=fill_color)
        self.badge_canvas.config(bg=fill_color)
        self.btn_rot.config(bg=fill_color, fg="white" if selected else COLORS["BLUE"])
        
        # Redraw badge with new colors
        self._draw_badge(self.page_num + 1)

    def show_context_menu(self, event):
        """Show the right-click context menu."""
        menu = tk.Menu(self, tearoff=0, bg=COLORS["SURFACE"], fg=COLORS["TEXT"], font=("Segoe UI Variable Text", 10))
        
        # Check if parent (EditorWindow) has the needed methods
        editor = self.winfo_toplevel()
        # Note: We assume the toplevel is the EditorWindow or has the logic
        
        cat_abbr = getattr(editor, "current_category_abbr", None)
        is_assigned = self.selected # In our context, selected means assigned to current category
        
        menu.add_command(label="🔍 Ver en grande", command=lambda: editor.show_zoom(self.page_num, mode="press"))
        menu.add_command(label="↻ Rotar 90°", command=lambda: self._handle_rotate(None))
        menu.add_separator()
        
        if is_assigned:
            menu.add_command(label="🔝 Mover al principio", command=lambda: editor.move_page_to_limit(self.page_num, "top"))
            menu.add_command(label="🔚 Mover al final", command=lambda: editor.move_page_to_limit(self.page_num, "bottom"))
            menu.add_separator()
            menu.add_command(label="❌ Quitar de esta categoría", command=lambda: self._handle_click(event))
        else:
            menu.add_command(label="✅ Asignar aquí", command=lambda: self._handle_click(event))
            
        menu.post(event.x_root, event.y_root)

# --- WINDOWS ---
class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, on_update):
        super().__init__(parent)
        self.title("Ajustes")
        self.geometry("350x450")
        self.resizable(False, False)
        self.configure(bg=COLORS["BG"])
        self.on_update = on_update
        self.grab_set()

        # Center on parent
        self.transient(parent)
        
        container = tk.Frame(self, bg=COLORS["BG"], padx=30, pady=30)
        container.pack(fill="both", expand=True)

        tk.Label(container, text="Ajustes", font=FONTS["TITLE"], bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(anchor="w", pady=(0, 20))

        # Theme Section
        tk.Label(container, text="Apariencia", font=FONTS["BOLD"], bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(anchor="w", pady=(10, 5))
        
        self.theme_var = tk.StringVar(value=CURRENT_THEME)
        tk.Radiobutton(container, text="Modo Claro", variable=self.theme_var, value="light", bg=COLORS["BG"], fg=COLORS["TEXT"], selectcolor=COLORS["SURFACE"], command=self.save).pack(anchor="w", padx=10)
        tk.Radiobutton(container, text="Modo Oscuro", variable=self.theme_var, value="dark", bg=COLORS["BG"], fg=COLORS["TEXT"], selectcolor=COLORS["SURFACE"], command=self.save).pack(anchor="w", padx=10, pady=(0, 20))

        # Animations Section
        tk.Label(container, text="Interfaz", font=FONTS["BOLD"], bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(anchor="w", pady=(10, 5))
        
        self.anim_var = tk.BooleanVar(value=ANIMATIONS_ENABLED)
        tk.Checkbutton(container, text="Activar Animaciones", variable=self.anim_var, onvalue=True, offvalue=False, bg=COLORS["BG"], fg=COLORS["TEXT"], selectcolor=COLORS["SURFACE"], command=self.save).pack(anchor="w", padx=10)
        tk.Label(container, text="Efectos de aparición y transiciones suaves", font=("Segoe UI Variable Text", 8), bg=COLORS["BG"], fg=COLORS["TEXT_SECONDARY"]).pack(anchor="w", padx=30)

        # Footer
        footer = tk.Frame(container, bg=COLORS["BG"])
        footer.pack(side="bottom", fill="x", pady=20)
        
        tk.Label(footer, text=f"Versión {APP_VERSION}", font=("Segoe UI Variable Text", 8), bg=COLORS["BG"], fg=COLORS["TEXT_SECONDARY"]).pack()
        RoundedButton(footer, "REINSTALAR APLICACIÓN", command=self.reinstall_app, color=COLORS["ACCENT"], fg_color=COLORS["BLUE"], width=200).pack(pady=5)
        RoundedButton(footer, "CERRAR", command=self.destroy, width=200).pack(pady=10)

    def reinstall_app(self):
        """Forces the update dialog even if versions match"""
        messagebox.showinfo("Reinstalación", "Para reinstalar, ejecute 'itmq_updater.py' o descargue la versión más reciente.")
        # updater.force_reinstall(self.master) # Removed as updater.py is missing

    def save(self):
        global CURRENT_THEME, ANIMATIONS_ENABLED, COLORS, UI_SETTINGS
        CURRENT_THEME = self.theme_var.get()
        ANIMATIONS_ENABLED = self.anim_var.get()
        COLORS = THEMES[CURRENT_THEME]
        
        UI_SETTINGS["theme"] = CURRENT_THEME
        UI_SETTINGS["animations"] = ANIMATIONS_ENABLED
        save_settings(UI_SETTINGS)
        
        self.configure(bg=COLORS["BG"])
        for child in self.winfo_children():
            if isinstance(child, tk.Frame):
                child.configure(bg=COLORS["BG"])
                for g in child.winfo_children():
                    if isinstance(g, (tk.Label, tk.Radiobutton, tk.Checkbutton)):
                        if g.master == child or (isinstance(g.master, tk.Frame) and g.master.master == child):
                             g.configure(bg=COLORS["BG"], fg=COLORS["TEXT"], selectcolor=COLORS["SURFACE"] if not isinstance(g, tk.Label) else None)
                    if isinstance(g, tk.Frame):
                        g.configure(bg=COLORS["BG"])
                        for gg in g.winfo_children():
                            if isinstance(gg, tk.Label):
                                gg.configure(bg=COLORS["BG"], fg=COLORS["TEXT"])
        
        self.on_update()

class ManualInputWindow(tk.Toplevel):
    def __init__(self, parent, page_obj=None, page_num=None, engine=None, suggested_val=None):
        super().__init__(parent)
        self.title("DATOS DEL TITULAR")
        self.state('zoomed')
        self.configure(bg=COLORS["BG"])
        self.result = None
        self.page_num = page_num
        self.engine = engine
        self.grab_set()
        
        left = tk.Frame(self, bg=COLORS["BG"])
        left.pack(side="left", fill="both", expand=True)
        
        if page_obj and engine:
             HighResCanvas(left, page_obj, page_num, engine).pack(fill="both", expand=True, padx=20, pady=20)
        else:
             tk.Label(left, text="Vista Previa No Disponible", font=FONTS["TITLE"], bg=COLORS["BG"], fg=COLORS["TEXT_SECONDARY"]).pack(expand=True)

        right = tk.Frame(self, bg=COLORS["SURFACE"], width=500, padx=40, pady=60) # Increased width
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        tk.Label(right, text="Verificación de Datos", font=FONTS["TITLE"], bg=COLORS["SURFACE"], fg=COLORS["TEXT"]).pack(anchor="w")
        tk.Label(right, text="Ingrese los datos del titular para la carpeta:", font=FONTS["MAIN"], bg=COLORS["SURFACE"], fg=COLORS["TEXT_SECONDARY"]).pack(anchor="w", pady=(10, 20))
        
        # Helper for custom entries
        def create_field(label, var_ref=None, is_cedula=False):
            tk.Label(right, text=label, font=("Segoe UI Variable Text", 9, "bold"), bg=COLORS["SURFACE"], fg=COLORS["TEXT"]).pack(anchor="w")
            e = tk.Entry(right, font=("Segoe UI Variable Text", 14), bd=0, bg=COLORS["ACCENT"], fg=COLORS["TEXT"], highlightthickness=1, highlightbackground=COLORS["BORDER"], highlightcolor=COLORS["BLUE"])
            if is_cedula:
                e.config(font=("Segoe UI Variable Text", 20, "bold"), justify="center")
            e.pack(fill="x", pady=(5, 15), ipady=8 if is_cedula else 5)
            return e

        self.entry_surname = create_field("APELLIDOS:")
        self.entry_name = create_field("NOMBRES:")
        self.entry = create_field("NÚMERO DE CÉDULA:", is_cedula=True)

        if suggested_val: self.entry.insert(0, suggested_val)
        self.entry_surname.focus_set() # Focus surname first

        # Navigation logic
        self.entry_surname.bind("<Return>", lambda e: self.entry_name.focus_set())
        self.entry_name.bind("<Return>", lambda e: self.entry.focus_set())
        self.entry.bind("<Return>", lambda e: self.confirm())

        RoundedButton(right, "CONFIRMAR DATOS", command=self.confirm, width=400).pack(pady=20)
        RoundedButton(right, "ROTAR DOCUMENTO", command=self.rotate_pdf, color=COLORS["ACCENT"], fg_color=COLORS["BLUE"], width=400).pack(pady=5)
        RoundedButton(right, "CÉDULA GENÉRICA", command=self.generic, color=COLORS["ACCENT"], fg_color=COLORS["TEXT_SECONDARY"], width=400).pack(pady=5)

        tk.Label(right, text="[Click Derecho o ESC para Volver]", font=("Segoe UI Variable Text", 9), bg=COLORS["SURFACE"], fg=COLORS["TEXT_SECONDARY"]).pack(side="bottom", pady=20)

        # Global return removed to avoid accidental submission from other fields
        # self.bind("<Return>", lambda e: self.confirm()) 
        self.bind("<Button-3>", lambda e: self.destroy())
        self.bind("<Escape>", lambda e: self.destroy())

    def refresh_theme(self):
        self.configure(bg=COLORS["BG"])
        for child in self.winfo_children():
            if isinstance(child, tk.Frame):
                is_right = child.pack_info().get("side") == "right"
                child.configure(bg=COLORS["SURFACE"] if is_right else COLORS["BG"])
                for grand in child.winfo_children():
                    if isinstance(grand, tk.Label):
                        # Simple heuristic for theme refresh
                        grand.configure(bg=grand.master["bg"], fg=COLORS["TEXT"] if grand["font"] != ("Segoe UI Variable Text", 9) else COLORS["TEXT_SECONDARY"])
                    elif isinstance(grand, tk.Entry):
                        grand.configure(bg=COLORS["ACCENT"], fg=COLORS["TEXT"], highlightbackground=COLORS["BORDER"], highlightcolor=COLORS["BLUE"])
                    elif isinstance(grand, RoundedButton):
                        grand.refresh_theme()
                    elif isinstance(grand, HighResCanvas):
                        grand.refresh_theme()

    def rotate_pdf(self):
        if self.engine and self.page_num is not None:
            self.engine.rotate_page(self.page_num)
            for w in self.winfo_children():
                if isinstance(w, tk.Frame):
                    for sub in w.winfo_children():
                        if isinstance(sub, HighResCanvas):
                            sub.render_image()
                            break

    def confirm(self):
        nombre = self.entry_name.get().strip().upper()
        apellido = self.entry_surname.get().strip().upper()
        cedula_raw = self.entry.get()
        cedula = re.sub(r'\D', '', cedula_raw)
        
        if not nombre or not apellido:
             messagebox.showwarning("Faltan Datos", "Por favor ingrese Nombres y Apellidos.")
             if not nombre: self.entry_name.focus_set()
             else: self.entry_surname.focus_set()
             return

        if cedula and 7 <= len(cedula) <= 12: # Slight range increase
            self.result = (cedula, nombre, apellido)
            self.destroy()
        else:
            messagebox.showerror("Error", "Cédula inválida. Verifique el número.")
            self.entry.focus_set()

    def generic(self):
        # Generic flow - still needs name? assumed generic
        self.result = ("GENERICO", "USUARIO", "GENERICO")
        self.destroy()

class EditorWindow(tk.Toplevel):
    def __init__(self, parent, file_path, on_finish, profile_name=DEFAULT_PROFILE, override_output_dir=None, document_type=None, custom_profile=None):
        super().__init__(parent)
        self.profile_name = profile_name
        
        # Use custom profile if provided, otherwise load from PROFILES
        if custom_profile:
            self.profile_data = custom_profile
        else:
            self.profile_data = PROFILES.get(profile_name, PROFILES[DEFAULT_PROFILE])
        
        self.categories = self.profile_data["CATEGORIES"]
        self.segments = self.profile_data["SEGMENTS"]
        self.override_output_dir = override_output_dir
        self.document_type = document_type  # Store document type
        
        # Build title with document type if provided
        title_parts = [f"Clasificador Pro: {os.path.basename(file_path)}"]
        if document_type:
            title_parts.append(f"[{document_type}]")
        title_parts.append(f"[{profile_name}]")
        self.title(" ".join(title_parts))

        self.state('zoomed')
        self.configure(bg=COLORS["BG"])
        self.engine = PDFEngine(file_path)
        self.on_finish = on_finish
        
        self.current_idx = 0 # 0-indexed across self.categories
        self.results = {} # abbr: [pages]
        self.tiles = []
        self.last_clicked_idx = None
        self.cedula = None
        self.nombre = None
        self.apellido = None
        self._focus_mode = "grid" # "grid" or "sidebar"
        self._active_preview = None
        self._preview_is_toggle = False
        # self._expanded_segments removed
        self._sb_widgets = {} # For widget reuse
        self.history = [] # For Undo
        self._last_width = 0 # For reflow debouncing
        self._resize_timer = None
        self.thumbnail_scale = 1.0 # Dynamic zoom state (0.5 to 2.0)

        self.setup_ui()
        self.load_pages()
        self.bind_keys()

    def bind_keys(self):
        self.bind("<Right>", self._on_key_right)
        self.bind("<Left>", self._on_key_left)
        # ... (rest of bind_keys logic not changed here, but ensuring indentation matches)
        self.bind("<Up>", self._on_key_up)
        self.bind("<Down>", self._on_key_down)
        self.bind("<Escape>", lambda e: self.prev_step())
        self.bind("<space>", lambda e: self.toggle_active_tile())
        self.bind("<Control-z>", lambda e: self.undo())
        self.bind("<Control-t>", lambda e: self.toggle_theme())
        self.bind("<Control-a>", lambda e: self.select_all())
        self.bind("<Return>", lambda e: self.next_step())
        self.bind("<Control-p>", lambda e: self.toggle_preview())


    def _on_key_right(self, e):
        # If in grid, move selection, otherwise ignored or custom
        self._move_grid_focus(1)

    def _on_key_left(self, e):
        self._move_grid_focus(-1)

    def _on_key_up(self, e):
        if self._focus_mode == "grid" and hasattr(self, "_grid_cols") and self._grid_cols > 0:
            self._move_grid_focus(-self._grid_cols)
        else:
            self.prev_step()

    def _on_key_down(self, e):
        if self._focus_mode == "grid" and hasattr(self, "_grid_cols") and self._grid_cols > 0:
            self._move_grid_focus(self._grid_cols)
        else:
            self.next_step()

    def _move_grid_focus(self, delta):
        visible = [t for t in self.tiles if not self.is_assigned(t.page_num)]
        if not visible: return
        
        # Initialize focus if none
        if not hasattr(self, "_focused_tile_idx") or self._focused_tile_idx is None:
            self._focused_tile_idx = 0
        else:
            # Clear old focus
            if self._focused_tile_idx < len(visible):
                visible[self._focused_tile_idx].set_focus(False)
            self._focused_tile_idx = (self._focused_tile_idx + delta) % len(visible)
        
        target = visible[self._focused_tile_idx]
        target.set_focus(True)
        # Ensure visible in canvas
        self._ensure_tile_visible(target)

    def _ensure_tile_visible(self, tile):
        self.canvas.update_idletasks()
        try:
            # Coordinates relative to the scrollable inner frame
            y = tile.winfo_y()
            h = tile.winfo_height()
            
            # Dimensions of the viewing area
            viewport_height = self.canvas.winfo_height()
            scroll_height = self.inner.winfo_height()
            
            if scroll_height <= viewport_height: return

            # Current scroll position (0.0 to 1.0)
            cur_top, cur_bottom = self.canvas.yview()
            
            # Convert boolean view bounds to pixels
            view_top_px = cur_top * scroll_height
            view_bottom_px = cur_bottom * scroll_height

            # Check if tile is out of view
            if y < view_top_px:
                # Scroll up to show top of tile
                new_pos = max(0, y / scroll_height)
                self.canvas.yview_moveto(new_pos)
            elif (y + h) > view_bottom_px:
                # Scroll down to show bottom of tile
                # Try to position it at the bottom, or just scroll enough to see it
                new_pos = min(1, (y + h - viewport_height) / scroll_height)
                self.canvas.yview_moveto(new_pos)
        except Exception:
            pass

    def select_all(self):
        self.history.append({k: list(v) for k, v in self.results.items()})
        visible = [t for t in self.tiles if not self.is_assigned(t.page_num)]
        curr_abbr = self.categories[self.current_idx][0]
        
        for t in visible:
            if not t.selected:
                t.set_state(True, "SELECCIONADO", COLORS["BLUE"])
                if curr_abbr not in self.results: self.results[curr_abbr] = []
                if t.page_num not in self.results[curr_abbr]:
                    self.results[curr_abbr].append(t.page_num)
        
        if curr_abbr in self.results: self.results[curr_abbr].sort()
        self.update_sidebar()

    def undo(self):
        if self.history:
            prev_results = self.history.pop()
            self.results = prev_results
            self.update_step_ui()

    def toggle_active_tile(self):
        # Toggle currently focused tile if it exists
        visible = [t for t in self.tiles if not self.is_assigned(t.page_num)]
        if hasattr(self, "_focused_tile_idx") and self._focused_tile_idx is not None:
            if self._focused_tile_idx < len(visible):
                self._handle_selection(visible[self._focused_tile_idx], False)
                return

        if visible:
            self._handle_selection(visible[0], False)

    def _handle_selection(self, tile, shift):
        self.history.append({k: list(v) for k, v in self.results.items()})
        if len(self.history) > 20: self.history.pop(0)
        
        curr_abbr = "CC" if self.current_idx == -1 else self.categories[self.current_idx][0]
        visible_tiles = [t for t in self.tiles if not self.is_assigned(t.page_num)]
        
        try:
            curr_tile_idx = next(i for i, t in enumerate(visible_tiles) if t == tile)
            # Update focus index to match selection
            if hasattr(self, "_focused_tile_idx") and self._focused_tile_idx < len(visible_tiles):
                visible_tiles[self._focused_tile_idx].set_focus(False)
            self._focused_tile_idx = curr_tile_idx
            tile.set_focus(True)
        except StopIteration: return 

        if shift and self.last_clicked_idx is not None:
            start = min(self.last_clicked_idx, curr_tile_idx)
            end = max(self.last_clicked_idx, curr_tile_idx)
            new_state = not tile.selected
            
            for i in range(start, end + 1):
                t = visible_tiles[i]
                self._update_page_assignment(t.page_num, curr_abbr, new_state)
                t.set_state(new_state, "SELECCIONADO" if new_state else None, COLORS["BLUE"])
        else:
            new_state = not tile.selected
            self._update_page_assignment(tile.page_num, curr_abbr, new_state)
            tile.set_state(new_state, "SELECCIONADO" if new_state else None, COLORS["BLUE"])


        self.last_clicked_idx = curr_tile_idx
        # if curr_abbr in self.results: self.results[curr_abbr].sort() # REMOVED RE-SORT
        
        # We need to full refresh to update numbers on all selected tiles
        self.update_step_ui()

    def _update_page_assignment(self, page_num, abbr, add):
        """Ensures a page is only in one category at a time."""
        # Always remove from other categories
        for a in list(self.results.keys()):
            if page_num in self.results[a]:
                self.results[a].remove(page_num)
        
        if add:
            if abbr not in self.results: self.results[abbr] = []
            if page_num not in self.results[abbr]:
                self.results[abbr].append(page_num)

    def setup_ui(self):
        # Header
        self.header = tk.Frame(self, bg=COLORS["SURFACE"], height=80, padx=40)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)
        # Progress Section
        self.prog_container = tk.Frame(self.header, bg=COLORS["SURFACE"])
        self.prog_container.pack(side="left", fill="y", padx=(20, 0))
        
        self.lbl_step = tk.Label(self.prog_container, text="Cargando...", font=FONTS["TITLE"], bg=COLORS["SURFACE"], fg=COLORS["TEXT"])
        self.lbl_step.pack(side="top", anchor="w", pady=(5, 0))
        
        self.prog_bar_canvas = tk.Canvas(self.prog_container, width=300, height=6, bg=COLORS["BORDER"], highlightthickness=0)
        self.prog_bar_canvas.pack(side="top", fill="x", pady=(2, 5))
        self.prog_fill = self.prog_bar_canvas.create_rectangle(0, 0, 0, 6, fill=COLORS["BLUE"], width=0)

        # Settings Button
        self.btn_settings = tk.Button(self.header, text="⚙️", font=("Segoe UI", 16), command=self.open_settings, bg=COLORS["SURFACE"], fg=COLORS["TEXT"], bd=0, cursor="hand2")
        self.btn_settings.pack(side="right", padx=5)
        Tooltip(self.btn_settings, "Ajustes del programa")

        # Help Button (Keyboard Legend)
        self.btn_help = tk.Button(self.header, text="❓", font=("Segoe UI", 16), command=self.show_keyboard_guide, bg=COLORS["SURFACE"], fg=COLORS["TEXT"], bd=0, cursor="hand2")
        self.btn_help.pack(side="right", padx=5)
        Tooltip(self.btn_help, "Atajos de teclado")

        # Main Layout
        self.main_container = tk.Frame(self, bg=COLORS["BG"])
        self.main_container.pack(fill="both", expand=True)

        # Sidebar
        self.sidebar = tk.Frame(self.main_container, bg=COLORS["SURFACE"], width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        
        self.sb_canvas = tk.Canvas(self.sidebar, bg=COLORS["SURFACE"], highlightthickness=0)
        self.sb_frame = tk.Frame(self.sb_canvas, bg=COLORS["SURFACE"])
        self.sb_scroll = ttk.Scrollbar(self.sidebar, orient="vertical", command=self.sb_canvas.yview)
        self.sb_canvas.configure(yscrollcommand=self.sb_scroll.set)
        
        self.sb_scroll.pack(side="right", fill="y")
        self.sb_canvas.pack(fill="both", expand=True)
        self.sb_canvas_win = self.sb_canvas.create_window((0,0), window=self.sb_frame, anchor="nw", width=210)
        
        # Enable scroll in sidebar
        self.sb_canvas.bind("<MouseWheel>", self._on_sidebar_scroll)
        self.sidebar.bind("<MouseWheel>", self._on_sidebar_scroll)

        # Grid Area
        self.grid_container = tk.Frame(self.main_container, bg=COLORS["BG"], padx=20, pady=20)
        self.grid_container.pack(side="left", fill="both", expand=True)
        
        self.canvas = tk.Canvas(self.grid_container, bg=COLORS["BG"], highlightthickness=0)
        self.scroll = ttk.Scrollbar(self.grid_container, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=COLORS["BG"])
        
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.scroll.pack(side="right", fill="y")
        self.canvas.pack(fill="both", expand=True)
        self.canvas_win = self.canvas.create_window((0,0), window=self.inner, anchor="nw")

        # Bottom Bar
        self.footer = tk.Frame(self, bg=COLORS["SURFACE"], height=90, padx=20)
        self.footer.pack(fill="x", side="bottom")
        self.footer.pack_propagate(False)
        
        # --- Navigation Buttons ---
        # << Anterior Segmento
        self.btn_prev_seg = RoundedButton(self.footer, "<< Segmento", command=self.prev_segment, color=COLORS["ACCENT"], fg_color=COLORS["TEXT_SECONDARY"], width=130)
        self.btn_prev_seg.pack(side="left", padx=5, pady=22)
        Tooltip(self.btn_prev_seg, "Volver al segmento anterior")

        # < Anterior Categ
        self.btn_prev = RoundedButton(self.footer, "< Anterior", command=self.prev_step, color=COLORS["ACCENT"], fg_color=COLORS["TEXT_SECONDARY"], width=130)
        self.btn_prev.pack(side="left", padx=5, pady=22)
        Tooltip(self.btn_prev, "Volver a la categoría anterior (Escape)")

        # Zoom Slider
        self.zoom_slider = tk.Scale(self.footer, from_=0.5, to=2.0, orient="horizontal", resolution=0.1, command=self._on_slider_zoom, showvalue=0, bg=COLORS["SURFACE"], highlightthickness=0, bd=0, length=120, activebackground=COLORS["ACCENT"], troughcolor=COLORS["BORDER"])
        self.zoom_slider.set(1.0)
        self.zoom_slider.pack(side="left", padx=15, pady=30)
        Tooltip(self.zoom_slider, "Ajustar tamaño de vista previa")

        # TERMINAR PROCESO (Center/Right-ish)
        self.btn_finish = RoundedButton(self.footer, "TERMINAR PROCESO", command=self.show_summary, color=COLORS["RED"], fg_color="#FFFFFF", width=180)
        self.btn_finish.pack(side="left", padx=20, pady=22)

        # Siguiente Categ >
        self.btn_next = RoundedButton(self.footer, "Siguiente >", command=self.next_step, width=130)
        self.btn_next.pack(side="right", padx=5, pady=20)
        Tooltip(self.btn_next, "Ir a la siguiente categoría (Enter)")
        
        # Siguiente Segmento >>
        self.btn_next_seg = RoundedButton(self.footer, "Segmento >>", command=self.next_segment, width=130, color=COLORS["BLUE_LIGHT"], fg_color=COLORS["BLUE"])
        self.btn_next_seg.pack(side="right", padx=5, pady=20)
        Tooltip(self.btn_next_seg, "Saltar al siguiente segmento")

        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Control-MouseWheel>", self._on_ctrl_scroll) # Bind Zoom
        self.sb_canvas.bind("<Button-1>", lambda e: self._set_focus_mode("sidebar"))
        
        # Enable Global Scroll in Grid Area
        self._bind_scroll_recursive(self.grid_container)
        self._bind_scroll_recursive(self.inner)
        
        # Track scroll for lazy loading
        self.canvas.configure(yscrollcommand=self._on_scroll)

    def _set_focus_mode(self, mode):
        self._focus_mode = mode
        # If switching to grid, highlight current focus if none
        if mode == "grid" and (not hasattr(self, "_focused_tile_idx") or self._focused_tile_idx is None):
            self._move_grid_focus(0)

    def _on_scroll(self, *args):
        self.scroll.set(*args)
        self.update_lazy_loading()

    def _on_resize(self, event):
        if self._resize_timer: self.after_cancel(self._resize_timer)
        self._resize_timer = self.after(100, self._perform_resize)

    def _perform_resize(self):
        self.reflow()
        self.update_lazy_loading()

    def update_lazy_loading(self):
        v_start = self.canvas.yview()[0]
        v_end = self.canvas.yview()[1]
        
        sr = self.canvas.bbox("all")
        if not sr: return
        total_h = sr[3] - sr[1]
        
        pixel_start = v_start * total_h
        pixel_end = v_end * total_h
        
        ch = self.canvas.winfo_height()
        # Viewport-aware buffer
        visible_range = (pixel_start - ch, pixel_end + ch)
        
        # Determine render quality based on zoom
        # Base scale 0.25 (for ~200px), adjust by zoom
        render_scale = 0.25 * self.thumbnail_scale

        for t in self.tiles:
            if not t.winfo_exists(): continue
            ty = t.winfo_y()
            # Check visibility + unload if hidden
            if visible_range[0] <= ty <= visible_range[1]:
                # If visible but scale changed significantly, we might want to re-render?
                # For now, just ensuring it is rendered.
                t.trigger_render(scale=render_scale)
            else:
                t.unload_image()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _on_ctrl_scroll(self, event):
        # Dynamic Zoom
        if event.delta > 0:
            self.thumbnail_scale = min(2.0, self.thumbnail_scale + 0.1)
        else:
            self.thumbnail_scale = max(0.5, self.thumbnail_scale - 0.1)
            
        # Sync slider if it exists
        if hasattr(self, "zoom_slider"):
            self.zoom_slider.set(self.thumbnail_scale)
            
        self.reflow(force=True)
        self.update_lazy_loading()

    def _on_slider_zoom(self, val):
        self.thumbnail_scale = float(val)
        self.reflow(force=True)
        self.update_lazy_loading()

    def _on_sidebar_scroll(self, event):
        self.sb_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _bind_scroll_recursive(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
        widget.bind("<Control-MouseWheel>", self._on_ctrl_scroll, add="+")
        for child in widget.winfo_children():
            self._bind_scroll_recursive(child)

    def open_settings(self):
        SettingsWindow(self, self.refresh_ui_theme)

    def toggle_theme(self):
        # Kept for backward compatibility/keybinds but routes to settings
        global COLORS, CURRENT_THEME
        CURRENT_THEME = "dark" if CURRENT_THEME == "light" else "light"
        COLORS = THEMES[CURRENT_THEME]
        UI_SETTINGS["theme"] = CURRENT_THEME
        save_settings(UI_SETTINGS)
        self.refresh_ui_theme()

    def refresh_ui_theme(self):
        # Update ttk styles for scrollbars and progress bars
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TProgressbar", thickness=8, troughcolor=COLORS["BORDER"], background=COLORS["BLUE"], borderwidth=0)
        style.configure("Vertical.TScrollbar", troughcolor=COLORS["BG"], background=COLORS["BORDER"], borderwidth=0, arrowcolor=COLORS["TEXT"])
        style.configure("Horizontal.TScrollbar", troughcolor=COLORS["BG"], background=COLORS["BORDER"], borderwidth=0, arrowcolor=COLORS["TEXT"])

        # Main window
        self.configure(bg=COLORS["BG"])
        
        # Header section
        self.header.config(bg=COLORS["SURFACE"])
        self.prog_container.config(bg=COLORS["SURFACE"])
        self.lbl_step.config(bg=COLORS["SURFACE"], fg=COLORS["TEXT"])
        
        # Progress bar
        self.prog_bar_canvas.config(bg=COLORS["BORDER"])
        self.prog_bar_canvas.itemconfig(self.prog_fill, fill=COLORS["BLUE"])
        
        # Header buttons
        self.btn_settings.config(bg=COLORS["SURFACE"], fg=COLORS["TEXT"])
        if hasattr(self, "btn_help"):
            self.btn_help.config(bg=COLORS["SURFACE"], fg=COLORS["TEXT"])
        
        # Main container
        self.main_container.config(bg=COLORS["BG"])
        
        # Sidebar
        self.sidebar.config(bg=COLORS["SURFACE"])
        self.sb_canvas.config(bg=COLORS["SURFACE"])
        self.sb_frame.config(bg=COLORS["SURFACE"])
        
        # Grid area
        self.grid_container.config(bg=COLORS["BG"])
        self.canvas.config(bg=COLORS["BG"])
        self.inner.config(bg=COLORS["BG"])
        
        # Footer
        self.footer.config(bg=COLORS["SURFACE"])
        
        # Navigation Buttons
        self.btn_prev_seg.refresh_theme(COLORS["ACCENT"])
        self.btn_prev.refresh_theme(COLORS["ACCENT"])
        self.btn_finish.refresh_theme(COLORS["RED"])
        self.btn_next.refresh_theme(COLORS["BLUE"])
        self.btn_next_seg.refresh_theme(COLORS["BLUE_LIGHT"])
        
        # Slider Refresh
        if hasattr(self, "zoom_slider"):
            self.zoom_slider.config(bg=COLORS["SURFACE"], activebackground=COLORS["ACCENT"], 
                                   troughcolor=COLORS["BORDER"], fg=COLORS["TEXT"])
        
        # Refresh all tiles
        for t in self.tiles: 
            t.refresh_theme()
        
        # Refresh sidebar content
        self.update_sidebar()

    def load_pages(self):
        def _load():
            try:
                total = self.engine.doc.page_count
                # Optimization: Use smaller step or remove delay entirely if animations are disabled
                step = 10 if ANIMATIONS_ENABLED else 0
                
                for i in range(total):
                    delay = (i * step)
                    self.after(delay, self._add_tile, i)
                
                final_delay = (total * step + 50) if ANIMATIONS_ENABLED else 50
                self.after(final_delay, self.update_step_ui)
                self.after(final_delay + 200, self.update_lazy_loading)
            except Exception as e:
                print(f"Load Error: {e}")
                self.after(0, lambda: messagebox.showerror("Error", f"Fallo al cargar: {e}"))
            
        threading.Thread(target=_load, daemon=True).start()

    def _add_tile(self, i):
        tile = PageTile(self.inner, i, self.engine, self._handle_selection, self.show_zoom, self.rotate_tile)
        self.tiles.append(tile)
        self._bind_scroll_recursive(tile)
        if ANIMATIONS_ENABLED:
             # Staggered reveal effect
             self.after(100, lambda: tile.lbl_img.config(fg=COLORS["BORDER"]))
             self.after(200, lambda: tile.bottom_bar.pack(fill="x", side="bottom"))

    def rotate_tile(self, tile):
        self.engine.rotate_page(tile.page_num)
        new_img = self.engine.get_page_preview(tile.page_num)
        tile.refresh_image(new_img)

    def reflow(self, force=False):
        if not self.inner.winfo_viewable(): return
        w = self.canvas.winfo_width()
        
        if not force and abs(w - self._last_width) < 10: return
        self._last_width = w
        
        # Dynamic Tile Size based on Zoom
        base_w = 210
        tile_w = int(base_w * self.thumbnail_scale)
        # Minimum width safety
        tile_w = max(100, tile_w)
        
        if w < tile_w: return
        
        cols = max(1, w // tile_w)
        self._grid_cols = cols 
        visible = [t for t in self.tiles if not self.is_assigned(t.page_num)]
        
        # Center alignment
        grid_w = cols * tile_w
        x_offset = max(0, (w - grid_w) // 2)
        
        for t in self.tiles: 
            t.grid_forget()
            # Update tile physical size if zoom changed
            # We access the internal image container to resize it
            # Aspect ratio 170/220 ~ 0.77
            img_w = int(170 * self.thumbnail_scale)
            img_h = int(220 * self.thumbnail_scale)
            t.img_container.config(width=img_w, height=img_h)
        
        for i, t in enumerate(visible):
            r, c = i // cols, i % cols
            t.grid(row=r, column=c, padx=10, pady=10)
        
        self.canvas.coords(self.canvas_win, x_offset, 0)
        self.canvas.itemconfig(self.canvas_win, width=grid_w)
        
        self.inner.update_idletasks()
        # Estimate height based on new scaled row height (approx 220 + padding + bottombar)
        row_h = int(290 * self.thumbnail_scale) 
        row_count = (len(visible) + cols - 1) // cols
        estimated_height = row_count * row_h
        self.canvas.config(scrollregion=(0, 0, w, estimated_height))

    def is_assigned(self, page_num):
        curr_abbr = self.categories[self.current_idx][0]
        # Special case for CTO/CTOF which share the same step view
        active_abbrs = {curr_abbr}
        if curr_abbr == "CTO": active_abbrs.add("CTOF")
        if curr_abbr == "CTOF": active_abbrs.add("CTO")
        
        for abbr, pages in self.results.items():
            if abbr not in active_abbrs and page_num in pages:
                return True
        return False

    def show_zoom(self, page_num, mode="toggle", duration=0):
        if mode == "press":
            if self._active_preview:
                self._active_preview.destroy()
                self._active_preview = None
                return
            self._preview_is_toggle = False
            self._open_zoom_window(page_num)
        
        elif mode == "release":
            if self._active_preview and not self._preview_is_toggle:
                if duration > 0.3: # Threshold for hold
                    self._active_preview.destroy()
                    self._active_preview = None
                else:
                    self._preview_is_toggle = True # Stay open as toggle
        
        elif mode == "hold_start":
            self._preview_is_toggle = False
            self._open_zoom_window(page_num)
            
        elif mode == "hold_end":
            if self._active_preview and not self._preview_is_toggle:
                self._active_preview.destroy()
                self._active_preview = None

    def _open_zoom_window(self, page_num):
        self._active_preview = win = tk.Toplevel(self)
        win.title(f"Aumento - Pág {page_num+1}")
        win.state('zoomed')
        win.configure(bg=COLORS["BG"])
        
        # Toolbar for zoom window
        toolbar = tk.Frame(win, bg=COLORS["SURFACE"], height=50)
        toolbar.pack(side="top", fill="x")
        
        viewer = HighResCanvas(win, self.engine.doc[page_num], page_num, self.engine)
        viewer.pack(fill="both", expand=True)
        
        # Tools
        tk.Label(toolbar, text=f"Página {page_num+1}", font=("Segoe UI Variable Text", 11, "bold"), bg=COLORS["SURFACE"], fg=COLORS["TEXT"]).pack(side="left", padx=20)
        
        btn_rot = tk.Button(toolbar, text="↻ Rotar", font=("Segoe UI", 10), command=viewer.rotate_pdf if hasattr(viewer, "rotate_pdf") else lambda: self._rotate_viewer(viewer), bg=COLORS["SURFACE"], fg=COLORS["BLUE"], bd=0, cursor="hand2")
        btn_rot.pack(side="left", padx=10)
        
        tk.Label(toolbar, text="|", fg=COLORS["BORDER"], bg=COLORS["SURFACE"]).pack(side="left")
        
        btn_zoom_in = tk.Button(toolbar, text="➕ Zoom", font=("Segoe UI", 10), command=lambda: viewer._on_zoom_manual(1.2), bg=COLORS["SURFACE"], fg=COLORS["TEXT"], bd=0, cursor="hand2")
        btn_zoom_in.pack(side="left", padx=10)
        
        btn_zoom_out = tk.Button(toolbar, text="➖ Zoom", font=("Segoe UI", 10), command=lambda: viewer._on_zoom_manual(0.8), bg=COLORS["SURFACE"], fg=COLORS["TEXT"], bd=0, cursor="hand2")
        btn_zoom_out.pack(side="left", padx=10)
        
        tk.Button(toolbar, text="CERRAR", font=("Segoe UI", 10, "bold"), command=win.destroy, bg=COLORS["SURFACE"], fg=COLORS["RED"], bd=0, cursor="hand2").pack(side="right", padx=20)

        # Permite volver (cerrar) con click derecho (toggle manual)
        win.bind("<Button-3>", lambda e: self.show_zoom(None, mode="press"))
        viewer.canvas.bind("<Button-3>", lambda e: self.show_zoom(None, mode="press"))
        
        def _on_destroy():
            if self._active_preview == win:
                self._active_preview = None
        win.bind("<Destroy>", lambda e: _on_destroy())

    def _rotate_viewer(self, viewer):
        """Helper to rotate the viewer and refresh."""
        viewer.engine.rotate_page(viewer.page_num)
        viewer.render_image()
        # Find the tile to mark it as needing re-render
        for t in self.tiles:
            if t.page_num == viewer.page_num:
                t.is_rendered = False
                t.trigger_render()
                break

    def update_step_ui(self):
        abbr, name = self.categories[self.current_idx]
        segment_name = next((s for s, items in self.segments.items() if abbr in items), "Proceso")
        
        self.lbl_step.config(text=f"{segment_name} | {abbr}: {name.upper()}")
        
        # Update Visual Progress Bar
        total = len(self.categories)
        if total > 0:
            progress = (self.current_idx + 1) / total
            self.prog_bar_canvas.coords(self.prog_fill, 0, 0, progress * 300, 6)
        
        selected = self.results.get(abbr, [])
        for t in self.tiles:
            if t.page_num in selected:
                # Find its index to show "1", "2", "3"
                idx = selected.index(t.page_num) + 1
                t.set_state(True, str(idx), COLORS["BLUE"])
            else:
                t.set_state(False, None, COLORS["BLUE"])
        
        self.reflow(force=True)
        self.update_sidebar()

    def update_sidebar(self):
        # 1. IDENTIFY CURRENT SEGMENT
        curr_abbr = self.categories[self.current_idx][0]
        current_seg_name = None
        current_seg_abbrs = []
        
        for seg, abbrs in self.segments.items():
            if curr_abbr in abbrs:
                current_seg_name = seg
                current_seg_abbrs = abbrs
                break
        
        if not current_seg_name: return # Should not happen

        # 2. CLEAR SIDEBAR only if necessary
        # Optimization: only rebuild if segment changed or results keys (counts) updated
        curr_state = (current_seg_name, self.current_idx, {a: len(p) for a, p in self.results.items() if a in current_seg_abbrs})
        if hasattr(self, "_last_sb_state") and self._last_sb_state == curr_state:
            return
        self._last_sb_state = curr_state

        # Batch destruction to avoid individual UI updates
        children = self.sb_frame.winfo_children()
        for w in children:
            w.destroy()
        self._sb_widgets = {}

        # 3. RENDER SEGMENT PROGRESS HEADER ( A - B - C - D )
        prog_frame = tk.Frame(self.sb_frame, bg=COLORS["SURFACE"], pady=10)
        prog_frame.pack(fill="x")
        
        # Extract letters (A, B, C...) from keys
        seg_keys = list(self.segments.keys())
        
        for i, seg_key in enumerate(seg_keys):
            letter = seg_key.split(".")[0].strip() # "A" from "A. Contrato..."
            is_active_seg = (seg_key == current_seg_name)
            
            # Simple button-like label
            l_bg = COLORS["ACCENT"] if is_active_seg else COLORS["Surface_2" if "Surface_2" in COLORS else "BORDER"]
            l_fg = COLORS["BLUE"] if is_active_seg else COLORS["TEXT_SECONDARY"]
            
            lbl = tk.Label(prog_frame, text=f" {letter} ", font=("Segoe UI Variable Text", 10, "bold"), bg=l_bg, fg=l_fg, width=3, cursor="hand2")
            lbl.pack(side="left", padx=2)
            
            # Bind click to jump to start of that segment
            # We need to find the index of the first category in that segment
            target_abbr = self.segments[seg_key][0]
            target_idx = -1
            for k, cat in enumerate(self.categories):
                if cat[0] == target_abbr:
                    target_idx = k
                    break
            
            if target_idx != -1:
                lbl.bind("<Button-1>", lambda e, idx=target_idx: self.go_to(idx))

        tk.Frame(self.sb_frame, height=1, bg=COLORS["BORDER"]).pack(fill="x", pady=5) # Separator

        # 4. RENDER CATEGORIES FOR CURRENT SEGMENT ONLY
        # Filter CATEGORIES to only those in current_seg_abbrs
        
        for abbr, name in self.categories:
            if abbr not in current_seg_abbrs: continue

            # Find global index
            idx = -1
            for i, v in enumerate(self.categories):
                if v[0] == abbr:
                    idx = i
                    break
            
            count = len(self.results.get(abbr, []))
            is_current = (idx == self.current_idx)
            c_bg = COLORS["BLUE_LIGHT" if is_current else "SURFACE"]
            
            container = tk.Frame(self.sb_frame, height=28, bg=c_bg)
            container.pack_propagate(False)
            container.pack(fill="x", padx=5, pady=1)

            # Icon/State
            prefix = "✅ " if count > 0 else ("🔹 " if is_current else "   ")
            
            lbl = tk.Label(container, text=f"{prefix}{name}", anchor="w", bg=c_bg)
            lbl.pack(side="left", padx=5, fill="both", expand=True)
            
            fg = COLORS["BLUE" if is_current else ("GREEN" if count > 0 else "TEXT")]
            font = ("Segoe UI Variable Text", 9, "bold") if is_current else ("Segoe UI Variable Text", 9)
            lbl.config(font=font, fg=fg)

            # Bind click
            for w in [container, lbl]:
                w.bind("<Button-1>", lambda e, i=idx: self.go_to(i))
                w.bind("<MouseWheel>", self._on_sidebar_scroll)

            if count > 0:
                cnt_lbl = tk.Label(container, text=str(count), font=("Segoe UI Variable Text", 8, "bold"), bg=c_bg, fg=fg)
                cnt_lbl.pack(side="right", padx=5)
                cnt_lbl.bind("<Button-1>", lambda e, i=idx: self.go_to(i))
            
        self.sb_canvas.config(scrollregion=self.sb_canvas.bbox("all"))

    def check_cedula_enforcement(self):
        """Enforces that a cedula is defined. If not, prompts the user."""
        if hasattr(self, "cedula") and self.cedula:
             return True
             
        # If not set, try to find a CC page to show in the popup
        cc_pages = self.results.get("CC", [])
        page_obj = None
        page_num = None
        match_val = None
        
        if cc_pages:
            page_num = cc_pages[0]
            page_obj = self.engine.doc[page_num]
            # Try to extract text for suggestion
            text = self.engine.get_text_clean(page_num)
            match = self.engine.id_regex.search(text.replace(".", "").replace(" ", ""))
            if match: match_val = match.group(0)
            
        win = ManualInputWindow(self, page_obj, page_num, self.engine, match_val)
        self.wait_window(win)
        
        if win.result:
            if isinstance(win.result, tuple):
                self.cedula, self.nombre, self.apellido = win.result
            else:
                self.cedula = win.result # Fallback
                self.nombre, self.apellido = "USUARIO", "GENERICO"
            return True
        return False

    def next_segment(self):
        if not self.check_cedula_enforcement(): return
        # Jump to start of next segment
        current_seg = None
        curr_abbr = self.categories[self.current_idx][0]
        
        # Find current segment
        for seg, abbrs in self.segments.items():
            if curr_abbr in abbrs:
                current_seg = seg
                break
        
        if not current_seg: return

        # Find next segment
        seg_names = list(self.segments.keys())
        try:
            curr_seg_idx = seg_names.index(current_seg)
            if curr_seg_idx < len(seg_names) - 1:
                next_seg_name = seg_names[curr_seg_idx + 1]
                target_abbr = self.segments[next_seg_name][0]
                
                # Find index of target_abbr in self.categories
                for i, (a, n) in enumerate(self.categories):
                    if a == target_abbr:
                        self.go_to(i)
                        return
        except ValueError: pass

    def prev_segment(self):
        # Jump to start of previous segment
        current_seg = None
        curr_abbr = self.categories[self.current_idx][0]
        
        # Find current segment
        for seg, abbrs in self.segments.items():
            if curr_abbr in abbrs:
                current_seg = seg
                break
        
        if not current_seg: return

        # Find prev segment
        seg_names = list(self.segments.keys())
        try:
            curr_seg_idx = seg_names.index(current_seg)
            if curr_seg_idx > 0:
                prev_seg_name = seg_names[curr_seg_idx - 1]
                target_abbr = self.segments[prev_seg_name][0]
                
                # Find index of target_abbr in self.categories
                for i, (a, n) in enumerate(self.categories):
                    if a == target_abbr:
                        self.go_to(i)
                        return
        except ValueError: pass

    def go_to(self, idx):
        self.current_idx = idx
        self.last_clicked_idx = None
        self.update_step_ui()

    def next_step(self):
        curr_abbr = self.categories[self.current_idx][0]
        
        # Enforce Cedula check (unless we are currently solving the CC step itself)
        if curr_abbr != "CC":
             if not self.check_cedula_enforcement(): return

        selected = self.results.get(curr_abbr, [])
        
        if curr_abbr == "CC":
            if not selected:
                messagebox.showwarning("Atención", "Seleccione la cédula")
                return
            page_idx = selected[0]
            text = self.engine.get_text_clean(page_idx)
            match = self.engine.id_regex.search(text.replace(".", "").replace(" ", ""))
            win = ManualInputWindow(self, self.engine.doc[page_idx], page_idx, self.engine, match.group(0) if match else None)
            self.wait_window(win)
            if not win.result: return
            if isinstance(win.result, tuple):
                self.cedula, self.nombre, self.apellido = win.result
            else:
                self.cedula = win.result
                self.nombre, self.apellido = "USUARIO", "GENERICO"
        else:
            if selected:
                if curr_abbr == "CTO":
                    if messagebox.askyesno("Contrato", "¿Este contrato está firmado?"):
                        # Move pages to CTOF
                        pages = self.results.pop("CTO", [])
                        self.results["CTOF"] = pages
            else:
                self.results.pop(curr_abbr, None)

        self.last_clicked_idx = None
        self.current_idx += 1
        
        # Auto-skip CTOF if it has no pages (meaning it wasn't used)
        while self.current_idx < len(self.categories):
             next_abbr = self.categories[self.current_idx][0]
             if next_abbr == "CTOF" and next_abbr not in self.results:
                 self.current_idx += 1
                 continue
             break

        if self.current_idx >= len(self.categories):
            # Final Form Verification check - Only for Gestion Humana
            if self.profile_name == "Gestion Humana":
                has_eps = "EPS" in self.results
                has_feps = "FEPS" in self.results
                has_ccf = "CCF" in self.results
                has_fccf = "FCCF" in self.results
                
                warns = []
                if has_eps and not has_feps: warns.append("No se asignó Formulario EPS (FEPS).")
                if has_ccf and not has_fccf: warns.append("No se asignó Formulario CCF (FCCF).")
                
                if warns:
                    msg = "\n".join(warns) + "\n\n¿Desea continuar y guardar de todos modos?"
                    if not messagebox.askyesno("Verificación de Formularios", msg):
                        self.current_idx -= 1
                        return


            self.show_summary() # Show summary instead of direct save
        else:
            self.update_step_ui()

    def prev_step(self):
        if self.current_idx > 0:
            self.last_clicked_idx = None
            self.current_idx -= 1
            self.update_step_ui()

    
    def show_summary(self):
        """Displays a summary of classified documents."""
        if not self.check_cedula_enforcement(): return

        summary_win = tk.Toplevel(self)
        summary_win.title("VERIFICACIÓN FINAL")
        summary_win.state('zoomed')
        summary_win.configure(bg=COLORS["BG"])
        
        # Header
        header = tk.Frame(summary_win, bg=COLORS["SURFACE"], height=80, padx=40)
        header.pack(fill="x")
        
        tk.Label(header, text="VERIFICACIÓN FINAL", font=FONTS["TITLE"], bg=COLORS["SURFACE"], fg=COLORS["TEXT"]).pack(side="left", pady=20)
        
        # Info
        inf = f"{self.apellido or ''} {self.nombre or ''} - {self.cedula or ''}".strip(" -")
        tk.Label(header, text=inf, font=("Segoe UI Variable Text", 14, "bold"), bg=COLORS["SURFACE"], fg=COLORS["BLUE"]).pack(side="right", pady=20)

        # Main horizontal container
        main_body = tk.Frame(summary_win, bg=COLORS["BG"])
        main_body.pack(fill="both", expand=True)

        # Content (Left Side - Previews)
        content = tk.Frame(main_body, bg=COLORS["BG"])
        content.pack(side="left", fill="both", expand=True, padx=20, pady=20)
        
        # Simple scrollable grid
        canvas = tk.Canvas(content, bg=COLORS["BG"], highlightthickness=0)
        scroll = ttk.Scrollbar(content, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=COLORS["BG"])
        
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        canvas.create_window((0,0), window=inner, anchor="nw")
        
        def _on_wheel(e): canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_wheel)
        inner.bind("<MouseWheel>", _on_wheel)

        # Sidebar (Right Side - Missing Categories)
        missing_sidebar = tk.Frame(main_body, bg=COLORS["SURFACE"], width=300, padx=20, pady=20)
        missing_sidebar.pack(side="right", fill="both")
        missing_sidebar.pack_propagate(False)

        tk.Label(missing_sidebar, text="CATEGORÍAS FALTANTES", font=("Segoe UI Variable Text", 12, "bold"), bg=COLORS["SURFACE"], fg=COLORS["RED"]).pack(pady=(0, 15))
        
        missing_scroll_frame = tk.Frame(missing_sidebar, bg=COLORS["SURFACE"])
        missing_scroll_frame.pack(fill="both", expand=True)
        
        missing_canvas = tk.Canvas(missing_scroll_frame, bg=COLORS["SURFACE"], highlightthickness=0)
        missing_sb = ttk.Scrollbar(missing_scroll_frame, orient="vertical", command=missing_canvas.yview)
        missing_inner = tk.Frame(missing_canvas, bg=COLORS["SURFACE"])
        
        missing_canvas.configure(yscrollcommand=missing_sb.set)
        missing_sb.pack(side="right", fill="y")
        missing_canvas.pack(fill="both", expand=True)
        missing_canvas.create_window((0,0), window=missing_inner, anchor="nw", width=260)

        missing_list = [name for abbr, name in self.categories if (abbr not in self.results or not self.results[abbr])]
        if not missing_list:
            tk.Label(missing_inner, text="¡Ninguna! Todo completo.", font=("Segoe UI Variable Text", 10, "italic"), bg=COLORS["SURFACE"], fg=COLORS["GREEN"]).pack(pady=10)
        else:
            for m_name in missing_list:
                tk.Label(missing_inner, text=f"• {m_name}", font=("Segoe UI Variable Text", 10), bg=COLORS["SURFACE"], fg=COLORS["TEXT"], anchor="w", wraplength=240, justify="left").pack(fill="x", pady=2)

        missing_inner.update_idletasks()
        missing_canvas.config(scrollregion=missing_canvas.bbox("all"))

        # Populate with categories
        r = 0
        sorted_cats = [c for c in self.categories if c[0] in self.results and self.results[c[0]]]
        
        if not sorted_cats:
             tk.Label(inner, text="No hay categorías seleccionadas.", font=("Segoe UI Variable Text", 12), bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(pady=50)

        for abbr, name in sorted_cats:
            pages = self.results[abbr]
            if not pages: continue
            
            # Category Header
            tk.Label(inner, text=f"{name} ({abbr})", font=("Segoe UI Variable Text", 11, "bold"), bg=COLORS["BG"], fg=COLORS["TEXT"]).grid(row=r, column=0, sticky="w", padx=10, pady=(20, 5))
            r += 1
            
            # Thumbs row
            row_frame = tk.Frame(inner, bg=COLORS["BG"])
            row_frame.grid(row=r, column=0, sticky="w", padx=10)
            
            def swap_page(a_abbr, idx1, idx2):
                lst = self.results[a_abbr]
                if 0 <= idx1 < len(lst) and 0 <= idx2 < len(lst):
                    lst[idx1], lst[idx2] = lst[idx2], lst[idx1]
                    summary_win.destroy()
                    self.show_summary() # Refresh
            
            for i, p_num in enumerate(pages):
                # Small thumbnail logic
                f = tk.Frame(row_frame, bg=COLORS["SURFACE"], bd=1, relief="solid")
                f.pack(side="left", padx=5)
                
                # Controls overlay
                ctrl = tk.Frame(f, bg=COLORS["ACCENT"], height=20)
                ctrl.pack(side="top", fill="x")
                
                if i > 0:
                    lb = tk.Label(ctrl, text="<", font=("bold", 8), bg=COLORS["ACCENT"], fg=COLORS["BLUE"], cursor="hand2")
                    lb.pack(side="left", padx=2)
                    lb.bind("<Button-1>", lambda e, a=abbr, x=i: swap_page(a, x, x-1))
                
                tk.Label(ctrl, text=str(i+1), font=("Segoe UI Variable Text", 8, "bold"), bg=COLORS["ACCENT"], fg=COLORS["TEXT"]).pack(side="left", expand=True)

                if i < len(pages) - 1:
                    rb = tk.Label(ctrl, text=">", font=("bold", 8), bg=COLORS["ACCENT"], fg=COLORS["BLUE"], cursor="hand2")
                    rb.pack(side="right", padx=2)
                    rb.bind("<Button-1>", lambda e, a=abbr, x=i: swap_page(a, x, x+1))

                try:
                    img_pil = self.engine.get_page_preview(p_num, scale=0.3)
                    img_tk = ImageTk.PhotoImage(img_pil)
                    l = tk.Label(f, image=img_tk, bg=COLORS["SURFACE"], cursor="hand2")
                    l.image = img_tk # Keep ref
                    l.pack()
                    
                    # Zoom bindings
                    l.bind("<Button-3>", lambda e, p=p_num: self.show_summary_zoom(p, "press"))
                    l.bind("<ButtonRelease-3>", lambda e, p=p_num: self.show_summary_zoom(p, "release"))
                    
                except Exception as e:
                    print(f"Summary preview error: {e}")
                    tk.Label(f, text=f"Pág {p_num+1}", width=10, height=5).pack()
                
                tk.Label(f, text=f"Orig: {p_num+1}", font=("Segoe UI Variable Text", 7), bg=COLORS["SURFACE"]).pack()
            
            r += 1

        inner.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

        # Footer Actions
        footer = tk.Frame(summary_win, bg=COLORS["SURFACE"], height=90)
        footer.pack(fill="x", side="bottom")
        
        RoundedButton(footer, "VOLVER A EDITAR", command=summary_win.destroy, color=COLORS["ACCENT"], fg_color=COLORS["TEXT_SECONDARY"], width=200).pack(side="left", padx=40, pady=20)
        RoundedButton(footer, "CONFIRMAR Y GUARDAR", command=lambda: [summary_win.destroy(), self.save()], color=COLORS["GREEN"], fg_color="#FFFFFF", width=250).pack(side="right", padx=40, pady=20)

    def show_summary_zoom(self, page_num, mode):
        """ Handles right-click zoom in summary window. """
        if mode == "press":
            if hasattr(self, '_sum_zoom_win') and self._sum_zoom_win:
                self._sum_zoom_win.destroy()
            
            self._sum_zoom_win = tk.Toplevel(self)
            self._sum_zoom_win.overrideredirect(True)
            self._sum_zoom_win.config(bg=COLORS["BORDER"])
            
            # Get big image
            try:
                img = self.engine.get_page_preview(page_num, scale=1.5)
                lbl = tk.Label(self._sum_zoom_win, image=img, bg=COLORS["BORDER"], bd=2, relief="solid")
                lbl.image = img
                lbl.pack()
                
                # Center on mouse
                mx, my = self.winfo_pointerx(), self.winfo_pointery()
                w, h = img.width(), img.height()
                
                # Adjust position to not go offscreen
                sw = self.winfo_screenwidth()
                sh = self.winfo_screenheight()
                
                x = mx - w//2
                y = my - h//2
                
                if x < 0: x = 10
                if y < 0: y = 10
                if x+w > sw: x = sw - w - 10
                if y+h > sh: y = sh - h - 10
                
                self._sum_zoom_win.geometry(f"{w}x{h}+{x}+{y}")
                
            except Exception as e:
                print(f"Zoom error: {e}")
                self._sum_zoom_win.destroy()
                
        elif mode == "release":
            if hasattr(self, '_sum_zoom_win') and self._sum_zoom_win:
                self._sum_zoom_win.destroy()
                self._sum_zoom_win = None

    def save(self):
        if not self.check_cedula_enforcement(): return

        self.btn_next.set_state("disabled")
        self.btn_next.set_text("Comprimiendo...")
        
        # Add Progress Bar overlay
        self.progress_win = tk.Toplevel(self)
        self.progress_win.title("Guardando...")
        self.progress_win.geometry("400x150")
        self.progress_win.configure(bg=COLORS["SURFACE"])
        self.progress_win.transient(self)
        self.progress_win.grab_set()
        
        tk.Label(self.progress_win, text="Procesando archivos...", font=FONTS["BOLD"], bg=COLORS["SURFACE"], fg=COLORS["TEXT"]).pack(pady=20)
        self.pbar = ttk.Progressbar(self.progress_win, orient="horizontal", length=300, mode="determinate")
        self.pbar.pack(pady=10)
        
        def _save_task():
            try:
                if self.override_output_dir:
                    base_dir = self.override_output_dir
                else:
                    base_dir = os.path.dirname(self.engine.file_path)
                
                # New Naming Convention
                # file_name = os.path.splitext(os.path.basename(self.engine.file_path))[0] (Unused now)
                
                folder_name = f"{self.apellido} {self.nombre} {self.cedula}"
                folder_main = os.path.join(base_dir, folder_name)
                
                folder = os.path.join(folder_main, "HISTORIA LABORAL")
                os.makedirs(folder, exist_ok=True)
                
                items = list(self.results.items())
                total = len(items)
                
                for i, (abbr, pages) in enumerate(items):
                    if not pages:
                        continue
                        
                    out = fitz.open()
                    for p in pages: 
                        # Insert with rotation
                        out.insert_pdf(self.engine.doc, from_page=p, to_page=p)
                        if p in self.engine.rotations:
                            out[-1].set_rotation(self.engine.rotations[p])
                    
                    # Compression logic: Ez-save with garbage=4, clean=True
                    save_path = os.path.join(folder, f"{abbr} {self.cedula}.pdf")
                    out.save(save_path, garbage=4, deflate=True, clean=True)
                    out.close()
                    
                    self.after(0, lambda v=(i+1)*100/total: self.pbar.config(value=v))

                # Generate Process Record (Previously Missing Report)
                self.generate_process_record(folder_main)

                # Logging to history
                self.log_history(os.path.basename(self.engine.file_path), folder)
                
                self.after(0, self.finish_all)
            except Exception as e:
                print(f"Save Error: {e}")
                self.after(0, lambda: messagebox.showerror("Error al Guardar", f"Ocurrió un error crítico: {e}"))
                self.after(0, lambda: self.btn_next.set_state("normal"))
                self.after(0, lambda: self.progress_win.destroy())

        threading.Thread(target=_save_task, daemon=True).start()

    def generate_process_record(self, dest_folder):
        from datetime import datetime
        now = datetime.now()
        timestamp_safe = now.strftime("%Y-%m-%d_%H%M") # For filename
        timestamp_pretty = now.strftime("%Y-%m-%d %H:%M") # For content 24h format
        
        missing = []
        if "CC" not in self.results: missing.append("CÉDULA (CC)")
        for abbr, name in self.categories:
            if abbr not in self.results:
                missing.append(f"{name} ({abbr})")
        
        processed_count = len(self.results)
        
        record_name = f"REGISTRO {self.cedula} {timestamp_safe}.txt"
        report_path = os.path.join(dest_folder, record_name)
        
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(f"REGISTRO DE PROCESAMIENTO\n")
                f.write(f"Fecha: {timestamp_pretty}\n")
                f.write(f"Cédula: {self.cedula}\n")
                f.write("="*40 + "\n\n")
                
                if missing:
                    f.write("DOCUMENTOS FALTANTES:\n")
                    for item in missing:
                        f.write(f"[X] {item}\n")
                else:
                    f.write("Todos los documentos obligatorios presentes.\n")
                
                f.write("\n" + "="*40 + "\n")
                f.write("PÁGINAS PROCESADAS:\n")
                for abbr, pages in self.results.items():
                    if pages:
                        cat_name = next((name for a, name in self.categories if a == abbr), abbr)
                        f.write(f"- {cat_name} ({abbr}): {len(pages)} página(s)\n")
                
                f.write("\n" + "="*40 + "\n")
                f.write(f"Total Categorias Procesadas: {processed_count}\n")
            
            # Make read-only
            os.chmod(report_path, stat.S_IREAD)
        except Exception as e:
            print(f"Error creating record: {e}")

    def log_history(self, filename, folder):
        try:
            h_path = os.path.join(os.path.expanduser("~"), ".pdf_flow_history.json")
            history = []
            if os.path.exists(h_path):
                with open(h_path, "r") as f: history = json.load(f)
            
            from datetime import datetime
            history.insert(0, {"file": filename, "folder": folder, "cedula": self.cedula, "date": str(datetime.now())})
            with open(h_path, "w") as f: json.dump(history[:100], f)
        except Exception as e:
            print(f"History log error: {e}")

    def move_page_to_limit(self, page_num, limit):
        """Moves an assigned page to the beginning or end of its category list."""
        abbr, _ = self.categories[self.current_idx]
        if abbr not in self.results: return
        
        pages = self.results[abbr]
        if page_num not in pages: return
        
        pages.remove(page_num)
        if limit == "top":
            pages.insert(0, page_num)
        else:
            pages.append(page_num)
        
        self.update_step_ui()

    def show_keyboard_guide(self):
        """Show a dialog with available keyboard shortcuts."""
        help_win = tk.Toplevel(self)
        help_win.title("Guía de Atajos de Teclado")
        help_win.geometry("450x400")
        help_win.resizable(False, False)
        help_win.configure(bg=COLORS["BG"])
        help_win.transient(self)
        help_win.grab_set()

        # Center help window
        x = self.winfo_x() + (self.winfo_width() // 2) - 225
        y = self.winfo_y() + (self.winfo_height() // 2) - 200
        help_win.geometry(f"+{x}+{y}")

        header = tk.Frame(help_win, bg=COLORS["BLUE"], height=60)
        header.pack(fill="x")
        tk.Label(header, text="Atajos de Teclado", font=("Segoe UI Variable Display", 16, "bold"), bg=COLORS["BLUE"], fg="white").pack(pady=15)

        content = tk.Frame(help_win, bg=COLORS["BG"], padx=30, pady=20)
        content.pack(fill="both", expand=True)

        shortcuts = [
            ("Enter", "Siguiente categoría / Terminar"),
            ("Escape", "Categoría anterior"),
            ("Flechas", "Navegar entre miniaturas"),
            ("Espacio", "Seleccionar / Deseleccionar pág."),
            ("Shift + Click", "Selección múltiple"),
            ("Ctrl + Z", "Deshacer última acción"),
            ("Ctrl + A", "Seleccionar todas las visibles"),
            ("Ctrl + T", "Cambiar entre modo Claro/Oscuro"),
            ("Click Der.", "Aumento rápido (Lupa)"),
            ("Scroll", "Navegar verticalmente"),
            ("Ctrl + Scroll", "Ajustar tamaño de miniaturas")
        ]

        for key, desc in shortcuts:
            row = tk.Frame(content, bg=COLORS["BG"])
            row.pack(fill="x", pady=3)
            tk.Label(row, text=key, font=("Segoe UI Variable Text", 10, "bold"), bg=COLORS["BG"], fg=COLORS["BLUE"], width=12, anchor="w").pack(side="left")
            tk.Label(row, text=desc, font=("Segoe UI Variable Text", 10), bg=COLORS["BG"], fg=COLORS["TEXT"], anchor="w").pack(side="left")

        RoundedButton(content, "ENTENDIDO", command=help_win.destroy, width=150).pack(pady=(20, 0))

    def finish_all(self):
        self.progress_win.destroy()
        self.engine.close()
        import gc
        gc.collect()
        self.destroy()
        self.on_finish()

class MainApp:
    def __init__(self, root):
        self.root = root
        status = itmq_license.get_license_status_text()
        self.root.title(f"ITMQ-GD v{APP_VERSION} ({status})")
        self.root.state('zoomed')
        self.root.minsize(800, 600)
        self.root.configure(bg=COLORS["BG"])
        self.queue = []
        self.selected_profile = tk.StringVar(value=DEFAULT_PROFILE)
        
        # Settings Button (Top Left) - Use place to ensure visibility
        self.btn_settings = tk.Button(root, text="⚙️", command=self.open_settings, bd=0, bg=COLORS["BG"], fg=COLORS["TEXT"], font=("Segoe UI", 14), cursor="hand2")
        self.btn_settings.place(x=20, y=20)
        
        # Footer
        self.lbl_footer = tk.Label(root, text="ITMQ - 2026 | v" + APP_VERSION, font=("Segoe UI", 8), fg=COLORS["TEXT_SECONDARY"], bg=COLORS["BG"])
        self.lbl_footer.pack(side="bottom", pady=15)
        
        # Container
        self.container = tk.Frame(root, bg=COLORS["BG"])
        self.container.pack(expand=True)
        
        self.lbl_title = tk.Label(self.container, text="Digitalizador", font=FONTS["TITLE"], bg=COLORS["BG"], fg=COLORS["TEXT"])
        self.lbl_title.pack()
        
        self.lbl_sub = tk.Label(self.container, text="Gestor Documental PDF", font=FONTS["SUBTITLE"], fg=COLORS["TEXT_SECONDARY"], bg=COLORS["BG"])
        self.lbl_sub.pack(pady=10)
        
        self.area = tk.Frame(self.container, bg=COLORS["SURFACE"], width=450, height=250, highlightthickness=1, highlightbackground=COLORS["BORDER"])
        self.area.pack(pady=30)
        self.area.pack_propagate(False)
        self.lbl_icon = tk.Label(self.area, text="📂", font=("Segoe UI", 64), bg=COLORS["SURFACE"], fg=COLORS["TEXT"])
        self.lbl_icon.pack(expand=True)
        
        self.btn_load = RoundedButton(self.container, "Iniciar Proceso", command=self.select_files, width=300)
        self.btn_load.pack()
        
        # Update Button
        self.btn_update = tk.Button(self.container, text="🔄 Buscar Actualizaciones", command=self.check_updates, 
                                     font=("Segoe UI", 9), bg=COLORS["SURFACE"], fg=COLORS["TEXT_SECONDARY"], 
                                     bd=0, cursor="hand2", pady=5)
        self.btn_update.pack(pady=10)
        
        # Auto-check for updates on startup (silent)
        self.root.after(2000, self.auto_check_updates)

    def open_settings(self):
        SettingsWindow(self.root, self.toggle_theme)

    def check_updates(self):
        """Manually triggered update check"""
        check_for_updates()
    
    def auto_check_updates(self):
        """Auto-check for updates on startup (silent)"""
        try:
            check_for_updates()
        except Exception as e:
            print(f"Auto update check failed: {e}")

    def toggle_theme(self):
        global COLORS, CURRENT_THEME
        # Theme may have changed in settings
        COLORS = THEMES[CURRENT_THEME]
        
        # Update ttk styles
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TProgressbar", thickness=8, troughcolor=COLORS["BORDER"], background=COLORS["BLUE"], borderwidth=0)
        style.configure("Vertical.TScrollbar", troughcolor=COLORS["BG"], background=COLORS["BORDER"], borderwidth=0, arrowcolor=COLORS["TEXT"])
        style.configure("Horizontal.TScrollbar", troughcolor=COLORS["BG"], background=COLORS["BORDER"], borderwidth=0, arrowcolor=COLORS["TEXT"])

        self.root.configure(bg=COLORS["BG"])
        self.container.config(bg=COLORS["BG"])
        self.lbl_title.config(bg=COLORS["BG"], fg=COLORS["TEXT"])
        self.lbl_sub.config(bg=COLORS["BG"], fg=COLORS["TEXT_SECONDARY"])
        self.area.config(bg=COLORS["SURFACE"], highlightbackground=COLORS["BORDER"])
        self.lbl_icon.config(bg=COLORS["SURFACE"], fg=COLORS["BLUE"])
        self.btn_load.refresh_theme(COLORS["BLUE"])
        self.btn_settings.config(bg=COLORS["BG"], fg=COLORS["TEXT"])
        self.lbl_footer.config(bg=COLORS["BG"], fg=COLORS["TEXT_SECONDARY"])
        self.btn_update.config(bg=COLORS["SURFACE"], fg=COLORS["TEXT_SECONDARY"])

    def select_files(self):
        paths = filedialog.askopenfilenames(filetypes=[("PDF", "*.pdf")])
        if not paths: return

        # Show document type selection dialog
        doc_type_dialog = DocumentTypeDialog(self.root)
        self.root.wait_window(doc_type_dialog)
        
        # If user cancelled the dialog, abort
        if not doc_type_dialog.selected_types:
            return
        
        # Join multiple types with ' + ' separator
        selected_doc_type = " + ".join(doc_type_dialog.selected_types)

        # If multiple files selected, ask if they're from one person
        if len(paths) > 1:
            single_person = messagebox.askyesno(
                "Tipo de Documentos",
                "¿Los documentos seleccionados son de una sola persona?\n\nSí = Unir PDFs y separar páginas\nNo = Procesar cada PDF por separado"
            )
            
            if single_person:
                # Merge all PDFs into one
                merged_path = self.merge_pdfs(list(paths))
                if merged_path:
                    # Pass origin directory as override and document type
                    origin_dir = os.path.dirname(paths[0])
                    self.queue.append((merged_path, origin_dir, selected_doc_type))
            else:
                # Add each PDF separately -> (path, None, doc_type)
                for p in paths:
                    self.queue.append((p, None, selected_doc_type))
        else:
            # Single file -> (path, None, doc_type)
            self.queue.append((paths[0], None, selected_doc_type))
        
        self.process_next()

    
    def process_next(self):
        if self.queue:
            item = self.queue.pop(0)
            if isinstance(item, tuple):
                # Handle both old 2-tuple and new 3-tuple formats
                if len(item) == 3:
                    path, override, doc_type = item
                else:
                    path, override = item
                    doc_type = None
            else:
                path, override, doc_type = item, None, None
            
            # Determine profile based on document type
            profile_to_use = self.selected_profile.get()
            custom_profile_data = None
            
            if doc_type:
                # Parse selected types
                selected_types = [t.strip() for t in doc_type.split('+')]
                
                # Single type selection - use specific profile
                if len(selected_types) == 1:
                    if "En Curso" in selected_types:
                        profile_to_use = "En Curso"
                    elif "Retiro" in selected_types:
                        profile_to_use = "Retiro"
                    elif "Ingreso" in selected_types:
                        profile_to_use = "Gestion Humana"
                
                # Multiple types - create combined profile
                elif len(selected_types) > 1:
                    combined_categories = []
                    combined_segments = {}
                    
                    for doc_type_name in selected_types:
                        if doc_type_name == "Ingreso":
                            profile = PROFILES["Gestion Humana"]
                        elif doc_type_name == "En Curso":
                            profile = PROFILES["En Curso"]
                        elif doc_type_name == "Retiro":
                            profile = PROFILES["Retiro"]
                        else:
                            continue
                        
                        # Add categories (avoid duplicates)
                        for cat in profile["CATEGORIES"]:
                            if cat not in combined_categories:
                                combined_categories.append(cat)
                        
                        # Add segments
                        for seg_name, seg_cats in profile["SEGMENTS"].items():
                            # Prefix segment name with document type for clarity
                            prefixed_seg_name = f"{doc_type_name} - {seg_name}"
                            combined_segments[prefixed_seg_name] = seg_cats
                    
                    # Create custom profile
                    custom_profile_data = {
                        "CATEGORIES": combined_categories,
                        "SEGMENTS": combined_segments
                    }
                    profile_to_use = f"Combinado ({doc_type})"
            
            # Pass custom profile data if created
            if custom_profile_data:
                EditorWindow(self.root, path, self.process_next, profile_name=profile_to_use, 
                             override_output_dir=override, document_type=doc_type, 
                             custom_profile=custom_profile_data)
            else:
                EditorWindow(self.root, path, self.process_next, profile_name=profile_to_use, 
                             override_output_dir=override, document_type=doc_type)
        else:
            messagebox.showinfo("Éxito", "Todos los archivos han sido procesados.")


class SplashScreen(tk.Toplevel):
    def __init__(self, parent, on_complete):
        super().__init__(parent)
        self.on_complete = on_complete
        self.overrideredirect(True)
        
        # Center splash
        w, h = 500, 300
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.configure(bg=COLORS["SURFACE"])
        
        # Set transparency support
        self.attributes("-alpha", 0.0)
        self.attributes("-topmost", True)
        
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "assets", "Intramaq-logo.png")
            if os.path.exists(logo_path):
                pil_img = Image.open(logo_path)
                pil_img.thumbnail((450, 250))
                self.tk_img = ImageTk.PhotoImage(pil_img)
                tk.Label(self, image=self.tk_img, bg=COLORS["SURFACE"]).pack(expand=True)
            else:
                tk.Label(self, text="DIGITALIZADOR INTRAMAQ", font=FONTS["TITLE"], bg=COLORS["SURFACE"], fg=COLORS["TEXT"]).pack(expand=True)
        except Exception as e:
            print(f"Splash screen error: {e}")
        
        self.start_animation()

    def start_animation(self):
        # Fade In (0.1s)
        self.fade_in(0)

    def fade_in(self, alpha):
        alpha += 0.2 # Faster fade in
        if alpha >= 1.0:
            self.attributes("-alpha", 1.0)
            self.after(400, self.start_fade_out) 
        else:
            self.attributes("-alpha", alpha)
            # Use a slightly faster interval for smoother fade in
            self.after(16, lambda: self.fade_in(alpha)) 

    def start_fade_out(self):
        self.fade_out(1.0)

    def fade_out(self, alpha):
        alpha -= 0.2 # Faster fade out
        if alpha <= 0:
            self.destroy()
            self.on_complete()
        else:
            self.attributes("-alpha", alpha)
            self.after(16, lambda: self.fade_out(alpha))

def main():
    check_single_instance()
    # High-DPI Awareness
    try:
        from ctypes import windll
        # SetProcessDpiAwareness(1) for Win 8.1 and 10+
        # SetProcessDPIAware() for Win Vista to 8
        try:
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            windll.user32.SetProcessDPIAware()
    except Exception as e:
        print(f"DPI Awareness error: {e}")

    root = tk.Tk()
    root.withdraw() # Hide main window initially
    
    # Fallback font handling - MUST be after root creation
    try:
        import tkinter.font as tkfont
        if "Segoe UI Variable Text" not in tkfont.families():
            global FONTS
            FONTS = {k: ("Segoe UI", v[1], v[2] if len(v)>2 else "normal") for k, v in FONTS.items()}
    except Exception as e:
        print(f"Font loading fallback error: {e}")
    
    def launch_main():
        root.deiconify()
        # Show success message if updated
        if "--updated" in sys.argv:
            messagebox.showinfo(
                "Actualización Exitosa", 
                f"¡La aplicación se ha actualizado correctamente a la versión {APP_VERSION}!"
            )
        MainApp(root)
    
    def resource_path(relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)

    # Check if logo exists for splash
    logo_path = resource_path(os.path.join("assets", "Intramaq-logo.png"))
    # Also check if it exists in current dir as fallback for icon
    if not os.path.exists(logo_path):
         logo_path = "Intramaq-logo.png"
         
    logo_exists = os.path.exists(logo_path)
    
    # 1. Check License first
    itmq_license.ensure_trial_initiated() # Automatically start 7-day trial if first time
    
    # Attempt automatic online activation if not activated
    if not itmq_license.is_activated():
        itmq_license.check_online_activation()
        
    if not itmq_license.is_activated():
        root.deiconify() # Show for dialog
        dialog = LicenseDialog(root)
        root.wait_window(dialog)
        if not itmq_license.is_activated():
            os._exit(0)
    
    # 2. Check for updates
    try:
        check_for_updates()
    except Exception as e:
        print(f"Update check failed: {e}")

    try:
        if logo_exists:
            try:
                # Set App Icon
                icon_img = ImageTk.PhotoImage(file=logo_path)
                root.iconphoto(True, icon_img)
            except Exception as e:
                print(f"Icon error: {e}")

            # time.sleep(0.5) # Removed to improve startup speed
            SplashScreen(root, launch_main)
        else:
            launch_main()
            
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Error Fatal en Proglite", f"Se produjo un error crítico:\n{e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
