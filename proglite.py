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
import updater

# --- GLOBAL SETTINGS & PERSISTENCE ---
# --- GLOBAL SETTINGS & PERSISTENCE ---
# Use LOCALAPPDATA to avoid permission issues in Program Files or Network Drives
APP_DATA_DIR = os.path.join(os.getenv('LOCALAPPDATA', os.path.expanduser('~')), "ClasificadorPDF")
if not os.path.exists(APP_DATA_DIR):
    try:
        os.makedirs(APP_DATA_DIR)
    except: pass

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
        except: pass
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    except: pass

UI_SETTINGS = load_settings()
CURRENT_THEME = UI_SETTINGS["theme"]
ANIMATIONS_ENABLED = UI_SETTINGS["animations"]

# --- CONFIGURATION & STYLING ---
THEMES = {
    "light": {
        "BLUE": "#E67E22",
        "BLUE_HOVER": "#D35400",
        "BLUE_LIGHT": "#FDEBD0",
        "RED": "#E74C3C",
        "GREEN": "#27AE60", # Nature Green
        "BG": "#F5F2EB", # Deeper Warm Cream (Less stark)
        "SURFACE": "#FDFBF7", # Very light warm white (Not pure white)
        "TEXT": "#2D3436", # Soft Charcoal
        "TEXT_SECONDARY": "#636E72", # Warm Gray
        "BORDER": "#E2DED5", # Warm Grayish Beige
        "ACCENT": "#EAE6DC" # Warm Beige Accent
    },
    "dark": {
        "BLUE": "#D35400", 
        "BLUE_HOVER": "#A04000",
        "BLUE_LIGHT": "#2C2C2E", # Dark gray
        "RED": "#C0392B",
        "GREEN": "#219150",
        "BG": "#1E1E1E", # Warm dark gray
        "SURFACE": "#2D2D2D",
        "TEXT": "#ECF0F1",
        "TEXT_SECONDARY": "#BDC3C7",
        "BORDER": "#424242",
        "ACCENT": "#333333"
    }
}

COLORS = THEMES[CURRENT_THEME]

FONTS = {
    "MAIN": ("Inter", 10),
    "BOLD": ("Inter", 10, "bold"),
    "TITLE": ("Inter", 22, "bold"),
    "SUBTITLE": ("Inter", 11),
}
# Fallback font handling
try:
    import tkinter.font as tkfont
    if "Inter" not in tkfont.families():
        FONTS = {k: ("Segoe UI", v[1], v[2] if len(v)>2 else "normal") for k, v in FONTS.items()}
except: pass

# --- PROFILES & CATEGORIES ---
PROFILES = {
    "Gestion Humana": {
        "CATEGORIES": [
            ("CC", "Cédula"), ("RQ", "Requisición"), ("HVI", "Hoja de vida interna"), 
            ("CTO", "Contrato laboral"), ("PRE", "Preaviso (Fijo)"), ("EXS", "Otro si (EXS)"),
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
            "A. Contrato y afiliaciones": ["CC", "RQ", "HVI", "CTO", "PRE", "EXS", "ARL", "FEPS", "EPS", "AFP", "FCCF", "CCF", "ADRES", "RUAF", "RC", "DOCB", "NOIB"],
            "B. Documentos de ingreso": ["HVE", "EI", "PSI", "PC", "AUT", "ANT", "CV", "RT", "CB", "LC"],
            "C. Certificaciones": ["CL", "CE"],
            "D. Comunicaciones": ["GEO", "PO", "APL"],
            "E. Documentos Adicionales": ["DOC"]
        }
    },
    "Simplificado": {
        "CATEGORIES": [
            ("CC", "Cédula"), ("CTO", "Contrato"), ("HVI", "Hoja de Vida"), ("EXT", "Otros")
        ],
        "SEGMENTS": {
            "Principales": ["CC", "CTO", "HVI"],
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
        except:
            text = ""
        
        clean = ''.join((c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')).lower()
        self.ocr_cache[page_num] = clean
        return clean

    def close(self):
        self.doc.close()

# --- CUSTOM WIDGETS ---
class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command=None, width=200, height=45, color=None, fg_color="white", **kwargs):
        self.color = color or COLORS["BLUE"]
        self.fg_color = fg_color or "white"
        
        super().__init__(parent, width=width, height=height, bg=parent["bg"], highlightthickness=0, cursor="hand2")
        self.command = command
        self.text = text
        self.state = "normal"
        self.draw()
        
        self.bind("<Button-1>", lambda e: self._on_click())
        self.bind("<Enter>", lambda e: self.draw(hover=True))
        self.bind("<Leave>", lambda e: self.draw(hover=False))

    def draw(self, hover=False):
        self.delete("all")
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        c = self.color if not hover else COLORS["BLUE_HOVER"]
        if self.state == "disabled": c = COLORS["BORDER"]
        
        self._draw_rounded_rect(2, 2, w-2, h-2, 12, fill=c)
        self.create_text(w/2, h/2, text=self.text, fill=self.fg_color if self.state != "disabled" else COLORS["TEXT_SECONDARY"], font=FONTS["BOLD"])

    def _on_click(self):
        if self.state == "normal" and self.command: self.command()

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

class HighResCanvas(tk.Frame):
    def __init__(self, parent, page_obj, page_num=None, engine=None):
        super().__init__(parent, bg=COLORS["BG"])
        self.page_obj = page_obj
        self.page_num = page_num
        self.engine = engine
        self.zoom_level = 2.0
        
        self.canvas = tk.Canvas(self, bg=COLORS["BG"], highlightthickness=0)
        self.v_scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.h_scroll = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        
        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll.pack(side="bottom", fill="x")
        self.canvas.pack(fill="both", expand=True)

        self.tk_img = None
        self.render_image()

        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Control-MouseWheel>", self._on_zoom)
        # Bind to parent too for better coverage
        self.bind("<MouseWheel>", self._on_mousewheel)

    def render_image(self):
        rot = 0
        if self.engine and self.page_num is not None:
            rot = self.engine.rotations.get(self.page_num, 0)
            
        matrix = fitz.Matrix(self.zoom_level, self.zoom_level).prerotate(rot)
        pix = self.page_obj.get_pixmap(matrix=matrix)
        img_pil = Image.open(io.BytesIO(pix.tobytes()))
        self.tk_img = ImageTk.PhotoImage(img_pil) 
        
        cw = self.winfo_width()
        ch = self.winfo_height()
        
        self.canvas.delete("all")
        self.canvas.create_image(max(0, (cw - self.tk_img.width()) // 2), 
                                 max(0, (ch - self.tk_img.height()) // 2), 
                                 image=self.tk_img, anchor="nw")
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

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

class PageTile(tk.Frame):
    def __init__(self, parent, page_num, engine, on_click, on_zoom, on_rotate):
        super().__init__(parent, bg=COLORS["SURFACE"], bd=0, highlightthickness=2, highlightbackground=COLORS["BORDER"])
        self.page_num = page_num
        self.engine = engine
        self.on_click = on_click
        self.on_zoom = on_zoom
        self.on_rotate = on_rotate
        self.selected = False
        self.is_rendered = False
        
        self.img_container = tk.Frame(self, bg=COLORS["SURFACE"], width=170, height=220)
        self.img_container.pack_propagate(False)
        self.img_container.pack(padx=8, pady=8)
        
        self.tk_img = None
        self.lbl_img = tk.Label(self.img_container, text="⏳", font=("Inter", 24), bg=COLORS["SURFACE"], fg=COLORS["BORDER"], cursor="hand2")
        self.lbl_img.pack(expand=True, fill="both")
        
        self.bottom_bar = tk.Frame(self, bg=COLORS["ACCENT"], height=32)
        self.bottom_bar.pack(fill="x", side="bottom")
        self.bottom_bar.pack_propagate(False)

        self.lbl_status = tk.Label(self.bottom_bar, text=f"{page_num+1}", bg=COLORS["ACCENT"], fg=COLORS["TEXT_SECONDARY"], font=("Inter", 9))
        self.lbl_status.pack(side="left", padx=10)
        
        self.btn_rot = tk.Label(self.bottom_bar, text="↻", bg=COLORS["ACCENT"], fg=COLORS["BLUE"], font=("Inter", 12), cursor="hand2")
        self.btn_rot.pack(side="right", padx=10)
        self.btn_rot.bind("<Button-1>", self._handle_rotate)

        for w in [self, self.lbl_img, self.lbl_status, self.img_container, self.bottom_bar]:
            w.bind("<Button-1>", self._handle_click)
            w.bind("<Button-3>", self._handle_right_press)
            w.bind("<ButtonRelease-3>", self._handle_right_release)
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

        if ANIMATIONS_ENABLED:
            # Set initial "invisible" state for animation
            self.lbl_img.config(fg=COLORS["BG"])
            self.bottom_bar.pack_forget()

    def _handle_right_press(self, e):
        self._right_click_time = time.time()
        self.on_zoom(self.page_num, mode="press")

    def _handle_right_release(self, e):
        duration = time.time() - getattr(self, "_right_click_time", 0)
        self.on_zoom(self.page_num, mode="release", duration=duration)

    def trigger_render(self, scale=0.25):
        if self.is_rendered: return
        self.is_rendered = True
        self.engine.async_render(self.page_num, scale, self._apply_image)

    def unload_image(self):
        """Free memory by unloading the PhotoImage."""
        if not self.is_rendered: return
        self.is_rendered = False
        self.tk_img = None
        self.lbl_img.config(image="", text="⏳")

    def _apply_image(self, img_pil):
        if not self.winfo_exists(): return
        self.tk_img = ImageTk.PhotoImage(img_pil)
        self.lbl_img.config(image=self.tk_img, text="")

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
        if not self.selected:
            self.config(highlightbackground=COLORS["BLUE"])

    def _on_leave(self, e):
        if not self.selected:
            self.config(highlightbackground=COLORS["BORDER"])

    def refresh_theme(self):
        self.config(bg=COLORS["SURFACE"], highlightbackground=COLORS["BLUE"] if self.selected else COLORS["BORDER"])
        self.img_container.config(bg=COLORS["SURFACE"])
        self.lbl_img.config(bg=COLORS["SURFACE"])
        self.bottom_bar.config(bg=COLORS["ACCENT"])
        self.lbl_status.config(bg=COLORS["ACCENT"], fg="white" if self.selected else COLORS["TEXT_SECONDARY"])
        self.btn_rot.config(bg=COLORS["ACCENT"])

    def set_focus(self, focused):
        """Sets a secondary highlight for keyboard focus."""
        if focused:
            self.config(highlightbackground=COLORS["BLUE"], highlightthickness=3)
        else:
            self.config(highlightbackground=COLORS["BLUE"] if self.selected else COLORS["BORDER"], highlightthickness=2)

    def set_state(self, selected, label_text=None, color=None):
        self.selected = selected
        fill = color if selected else COLORS["SURFACE"]
        bg_bottom = color if selected else COLORS["ACCENT"]
        fg = "white" if selected else COLORS["TEXT_SECONDARY"]
        txt = label_text or f"Página {self.page_num+1}"
        
        self.config(bg=fill, highlightbackground=color if selected else COLORS["BORDER"])
        self.img_container.config(bg=fill)
        self.lbl_img.config(bg=fill)
        self.bottom_bar.config(bg=bg_bottom)
        self.lbl_status.config(text=txt, bg=bg_bottom, fg=fg)
        self.btn_rot.config(bg=bg_bottom, fg="white" if selected else COLORS["BLUE"])

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
        tk.Label(container, text="Efectos de aparición y transiciones suaves", font=("Inter", 8), bg=COLORS["BG"], fg=COLORS["TEXT_SECONDARY"]).pack(anchor="w", padx=30)

        # Footer
        footer = tk.Frame(container, bg=COLORS["BG"])
        footer.pack(side="bottom", fill="x", pady=20)
        
        tk.Label(footer, text=f"Versión {updater.APP_VERSION}", font=("Inter", 8), bg=COLORS["BG"], fg=COLORS["TEXT_SECONDARY"]).pack()
        RoundedButton(footer, "CERRAR", command=self.destroy, width=200).pack(pady=10)

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
        self.title("VERIFICACIÓN DE CÉDULA")
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
             tk.Label(left, text="Ingrese el número de documento", font=FONTS["TITLE"], bg=COLORS["BG"], fg=COLORS["TEXT_SECONDARY"]).pack(expand=True)

        right = tk.Frame(self, bg=COLORS["SURFACE"], width=450, padx=40, pady=80)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        tk.Label(right, text="Identificación", font=FONTS["TITLE"], bg=COLORS["SURFACE"], fg=COLORS["TEXT"]).pack(anchor="w")
        tk.Label(right, text="Verifique o ingrese el número de cédula:", font=FONTS["MAIN"], bg=COLORS["SURFACE"], fg=COLORS["TEXT_SECONDARY"]).pack(anchor="w", pady=(20, 10))
        
        self.entry = tk.Entry(right, font=("Inter", 28, "bold"), justify="center", bd=0, bg=COLORS["ACCENT"], fg=COLORS["TEXT"], highlightthickness=2, highlightbackground=COLORS["BORDER"], highlightcolor=COLORS["BLUE"])
        self.entry.pack(fill="x", pady=30, ipady=10)
        if suggested_val: self.entry.insert(0, suggested_val)
        self.entry.focus_set()

        RoundedButton(right, "CONFIRMAR", command=self.confirm, width=370).pack(pady=10)
        RoundedButton(right, "ROTAR DOCUMENTO", command=self.rotate_pdf, color=COLORS["ACCENT"], fg_color=COLORS["BLUE"], width=370).pack(pady=5)
        RoundedButton(right, "CÉDULA GENÉRICA", command=self.generic, color=COLORS["ACCENT"], fg_color=COLORS["TEXT_SECONDARY"], width=370).pack(pady=5)

        tk.Label(right, text="[Click Derecho o ESC para Volver]", font=("Inter", 9), bg=COLORS["SURFACE"], fg=COLORS["TEXT_SECONDARY"]).pack(side="bottom", pady=20)

        self.bind("<Return>", lambda e: self.confirm())
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
                        grand.configure(bg=grand.master["bg"], fg=COLORS["TEXT"] if "Identificación" in grand["text"] else COLORS["TEXT_SECONDARY"])
                    elif isinstance(grand, tk.Entry):
                        grand.configure(bg=COLORS["ACCENT"], fg=COLORS["TEXT"], highlightbackground=COLORS["BORDER"], highlightcolor=COLORS["BLUE"])
                    elif isinstance(grand, RoundedButton):
                        grand.refresh_theme()
                    elif isinstance(grand, HighResCanvas):
                        grand.refresh_theme()

    def rotate_pdf(self):
        if self.engine and self.page_num is not None:
            self.engine.rotate_page(self.page_num)
            # Find the viewer component to re-render
            for w in self.winfo_children():
                if isinstance(w, tk.Frame): # The left frame
                    for sub in w.winfo_children():
                        if isinstance(sub, HighResCanvas):
                            sub.render_image()
                            break

    def confirm(self):
        val = re.sub(r'\D', '', self.entry.get())
        if val and 7 <= len(val) <= 10:
            self.result = val
            self.destroy()
        else:
            messagebox.showerror("Error", "Cédula inválida. Debe tener entre 7 y 10 dígitos.")
            self.entry.focus_set()

    def generic(self):
        val = self.entry.get().strip()
        if not val: val = "Generico"
        self.result = val
        self.destroy()

class EditorWindow(tk.Toplevel):
    def __init__(self, parent, file_path, on_finish, profile_name=DEFAULT_PROFILE):
        super().__init__(parent)
        self.profile_name = profile_name
        self.profile_data = PROFILES.get(profile_name, PROFILES[DEFAULT_PROFILE])
        self.categories = self.profile_data["CATEGORIES"]
        self.segments = self.profile_data["SEGMENTS"]
        
        self.title(f"Clasificador Pro: {os.path.basename(file_path)} [{profile_name}]")
        self.state('zoomed')
        self.configure(bg=COLORS["BG"])
        self.engine = PDFEngine(file_path)
        self.on_finish = on_finish
        
        self.current_idx = 0 # 0-indexed across self.categories
        self.results = {} # abbr: [pages]
        self.tiles = []
        self.last_clicked_idx = None
        self.cedula = None
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
        ty = tile.winfo_y()

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
        if curr_abbr in self.results: self.results[curr_abbr].sort()
        self.update_sidebar()

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
        self.lbl_step = tk.Label(self.header, text="Cargando...", font=FONTS["TITLE"], bg=COLORS["SURFACE"], fg=COLORS["TEXT"])
        self.lbl_step.pack(side="left", pady=15)

        # Settings Button
        self.btn_settings = tk.Button(self.header, text="⚙️", font=("Segoe UI", 16), command=self.open_settings, bg=COLORS["SURFACE"], fg=COLORS["TEXT"], bd=0, cursor="hand2")
        self.btn_settings.pack(side="right", padx=10)

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

        # < Anterior Categ
        self.btn_prev = RoundedButton(self.footer, "< Anterior", command=self.prev_step, color=COLORS["ACCENT"], fg_color=COLORS["TEXT_SECONDARY"], width=130)
        self.btn_prev.pack(side="left", padx=5, pady=22)

        # Zoom Slider
        self.zoom_slider = tk.Scale(self.footer, from_=0.5, to=2.0, orient="horizontal", resolution=0.1, command=self._on_slider_zoom, showvalue=0, bg=COLORS["SURFACE"], highlightthickness=0, bd=0, length=120, activebackground=COLORS["ACCENT"], troughcolor=COLORS["BORDER"])
        self.zoom_slider.set(1.0)
        self.zoom_slider.pack(side="left", padx=15, pady=30)

        # TERMINAR PROCESO (Center/Right-ish)
        self.btn_finish = RoundedButton(self.footer, "TERMINAR PROCESO", command=self.save, color=COLORS["RED"], fg_color="#FFFFFF", width=180)
        self.btn_finish.pack(side="left", padx=20, pady=22)

        # Siguiente Categ >
        self.btn_next = RoundedButton(self.footer, "Siguiente >", command=self.next_step, width=130)
        self.btn_next.pack(side="right", padx=5, pady=20)
        
        # Siguiente Segmento >>
        self.btn_next_seg = RoundedButton(self.footer, "Segmento >>", command=self.next_segment, width=130, color=COLORS["BLUE_LIGHT"], fg_color=COLORS["BLUE"])
        self.btn_next_seg.pack(side="right", padx=5, pady=20)

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

        self.configure(bg=COLORS["BG"])
        self.header.config(bg=COLORS["SURFACE"])
        self.lbl_step.config(bg=COLORS["SURFACE"], fg=COLORS["TEXT"])
        self.btn_settings.config(bg=COLORS["SURFACE"], fg=COLORS["TEXT"])
        self.main_container.config(bg=COLORS["BG"])
        self.sidebar.config(bg=COLORS["SURFACE"])
        self.sb_canvas.config(bg=COLORS["SURFACE"])
        self.sb_frame.config(bg=COLORS["SURFACE"])
        self.grid_container.config(bg=COLORS["BG"])
        self.canvas.config(bg=COLORS["BG"])
        self.inner.config(bg=COLORS["BG"])
        self.footer.config(bg=COLORS["SURFACE"])
        
        # Navigation Buttons Fix (names matched with setup_ui)
        self.btn_prev_seg.refresh_theme(COLORS["ACCENT"])
        self.btn_prev.refresh_theme(COLORS["ACCENT"])
        self.btn_finish.refresh_theme(COLORS["RED"])
        self.btn_next.refresh_theme(COLORS["BLUE"])
        self.btn_next_seg.refresh_theme(COLORS["BLUE_LIGHT"])
        
        # Slider Refresh
        if hasattr(self, "zoom_slider"):
            self.zoom_slider.config(bg=COLORS["SURFACE"], activebackground=COLORS["ACCENT"], troughcolor=COLORS["BORDER"], fg=COLORS["TEXT"])
        
        for t in self.tiles: t.refresh_theme()
        self.update_sidebar()

    def load_pages(self):
        def _load():
            try:
                total = self.engine.doc.page_count
                for i in range(total):
                    delay = (i * 30) if ANIMATIONS_ENABLED else 0
                    self.after(delay, self._add_tile, i)
                
                final_delay = (total * 30 + 100) if ANIMATIONS_ENABLED else 100
                self.after(final_delay, self.update_step_ui)
                self.after(final_delay + 500, self.update_lazy_loading)
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
        viewer = HighResCanvas(win, self.engine.doc[page_num], page_num, self.engine)
        viewer.pack(fill="both", expand=True)
        # Permite volver (cerrar) con click derecho (toggle manual)
        win.bind("<Button-3>", lambda e: self.show_zoom(None, mode="press"))
        viewer.canvas.bind("<Button-3>", lambda e: self.show_zoom(None, mode="press"))
        
        def _on_destroy():
            if self._active_preview == win:
                self._active_preview = None
        win.bind("<Destroy>", lambda e: _on_destroy())

    def update_step_ui(self):
        abbr, name = self.categories[self.current_idx]
        segment_name = next((s for s, items in self.segments.items() if abbr in items), "Proceso")
        
        self.lbl_step.config(text=f"{segment_name} | {abbr}: {name.upper()}")
        
        selected = self.results.get(abbr, [])
        for t in self.tiles:
            t.set_state(t.page_num in selected, "SELECCIONADO" if t.page_num in selected else None, COLORS["BLUE"])
        
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
        # Optimization: only rebuild if segment changed or counts updated
        curr_state = (current_seg_name, self.current_idx, {a: len(p) for a, p in self.results.items() if a in current_seg_abbrs})
        if hasattr(self, "_last_sb_state") and self._last_sb_state == curr_state:
            return
        self._last_sb_state = curr_state

        for w in self.sb_frame.winfo_children():
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
            
            lbl = tk.Label(prog_frame, text=f" {letter} ", font=("Inter", 10, "bold"), bg=l_bg, fg=l_fg, width=3, cursor="hand2")
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
            font = ("Inter", 9, "bold") if is_current else ("Inter", 9)
            lbl.config(font=font, fg=fg)

            # Bind click
            for w in [container, lbl]:
                w.bind("<Button-1>", lambda e, i=idx: self.go_to(i))
                w.bind("<MouseWheel>", self._on_sidebar_scroll)

            if count > 0:
                cnt_lbl = tk.Label(container, text=str(count), font=("Inter", 8, "bold"), bg=c_bg, fg=fg)
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
            self.cedula = win.result
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
            self.cedula = win.result
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

            self.save() # Direct save after last step
        else:
            self.update_step_ui()

    def prev_step(self):
        if self.current_idx > 0:
            self.last_clicked_idx = None
            self.current_idx -= 1
            self.update_step_ui()

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
                base_dir = os.path.dirname(self.engine.file_path)
                file_name = os.path.splitext(os.path.basename(self.engine.file_path))[0]
                # Incluir cédula en el nombre de la carpeta principal
                folder_main = os.path.join(base_dir, f"{file_name} {self.cedula}")
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
        except Exception as e:
            print(f"Error creating record: {e}")

    def log_history(self, filename, folder):
        try:
            h_path = os.path.join(os.path.expanduser("~"), ".pdf_flow_history.json")
            history = []
            if os.path.exists(h_path):
                with open(h_path, "r") as f: history = json.load(f)
            
            history.insert(0, {"file": filename, "folder": folder, "cedula": self.cedula, "date": str(fitz.now())})
            with open(h_path, "w") as f: json.dump(history[:100], f)
        except: pass

    def finish_all(self):
        self.progress_win.destroy()
        self.engine.close()
        self.destroy()
        self.on_finish()

class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Intramaq PDF Class")
        self.root.geometry("850x700")
        self.root.configure(bg=COLORS["BG"])
        self.queue = []
        self.selected_profile = tk.StringVar(value=DEFAULT_PROFILE)
        
        self.container = tk.Frame(root, bg=COLORS["BG"])
        self.container.pack(expand=True)
        
        self.lbl_title = tk.Label(self.container, text="Digitalizador", font=FONTS["TITLE"], bg=COLORS["BG"], fg=COLORS["TEXT"])
        self.lbl_title.pack()
        
        self.lbl_sub = tk.Label(self.container, text="Clasificacion de paquetes PDF", font=FONTS["SUBTITLE"], fg=COLORS["TEXT_SECONDARY"], bg=COLORS["BG"])
        self.lbl_sub.pack(pady=10)
        
        self.area = tk.Frame(self.container, bg=COLORS["SURFACE"], width=450, height=250, highlightthickness=1, highlightbackground=COLORS["BORDER"])
        self.area.pack(pady=30)
        self.area.pack_propagate(False)
        self.lbl_icon = tk.Label(self.area, text="📂", font=("Segoe UI", 64), bg=COLORS["SURFACE"], fg=COLORS["TEXT"])
        self.lbl_icon.pack(expand=True)
        
        self.btn_load = RoundedButton(self.container, "Iniciar Proceso", command=self.select_files, width=300)
        self.btn_load.pack()
        
        # Profile Selector
        tk.Label(self.container, text="Perfil de clasificación:", font=("Inter", 9), bg=COLORS["BG"], fg=COLORS["TEXT_SECONDARY"]).pack(pady=(20, 5))
        
        self.profile_menu = ttk.Combobox(self.container, textvariable=self.selected_profile, values=list(PROFILES.keys()), state="readonly", font=("Inter", 10), width=30)
        self.profile_menu.pack(pady=5)
        
        # Update button
        self.btn_update = tk.Button(self.container, text="🔄 Buscar Actualizaciones", command=self.check_updates, 
                                     font=("Segoe UI", 9), bg=COLORS["SURFACE"], fg=COLORS["TEXT_SECONDARY"], 
                                     bd=0, cursor="hand2", pady=5)
        self.btn_update.pack(pady=5)
        
        self.btn_settings = tk.Button(root, text="⚙️", command=self.open_settings, bd=0, bg=COLORS["BG"], fg=COLORS["TEXT"], font=("Segoe UI", 14), cursor="hand2")
        self.btn_settings.pack(side="top", anchor="nw", padx=20, pady=20)

        self.lbl_footer = tk.Label(root, text="Tomás Posada Castro - 2026 | v" + updater.APP_VERSION, font=("Segoe UI", 8), fg=COLORS["TEXT_SECONDARY"], bg=COLORS["BG"])
        self.lbl_footer.pack(side="bottom", pady=15)
        
        # Auto-check for updates on startup (silent)
        self.root.after(2000, self.auto_check_updates)

    def open_settings(self):
        SettingsWindow(self.root, self.toggle_theme)

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
        if paths:
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
                        self.queue.append(merged_path)
                else:
                    # Add each PDF separately
                    self.queue.extend(list(paths))
            else:
                # Single file, add directly
                self.queue.extend(list(paths))
            
            self.process_next()
    
    def merge_pdfs(self, paths):
        """Merge multiple PDFs into a single temporary PDF."""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_dir = os.path.join(os.path.expanduser("~"), "Documents", "Temp_PDF_Merged")
            os.makedirs(temp_dir, exist_ok=True)
            
            merged_name = f"Merged_{timestamp}.pdf"
            merged_path = os.path.join(temp_dir, merged_name)
            
            # Create merged document
            merged_doc = fitz.open()
            
            for pdf_path in paths:
                try:
                    doc = fitz.open(pdf_path)
                    merged_doc.insert_pdf(doc)
                    doc.close()
                except Exception as e:
                    print(f"Error merging {pdf_path}: {e}")
            
            # Get page count before closing
            total_pages = merged_doc.page_count
            
            merged_doc.save(merged_path)
            merged_doc.close()
            
            messagebox.showinfo("Éxito", f"Se unieron {len(paths)} archivos PDF.\nTotal de páginas: {total_pages}")
            return merged_path
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron unir los PDFs: {e}")
            return None
    
    def check_updates(self):
        """Manually check for updates."""
        has_update, data = updater.check_for_updates(silent=False)
        if has_update:
            updater.show_update_dialog(self.root, data)
    
    def auto_check_updates(self):
        """Auto-check for updates on startup (silent) in background thread."""
        threading.Thread(target=lambda: updater.auto_check_updates(self.root), daemon=True).start()


    def process_next(self):
        if self.queue:
            path = self.queue.pop(0)
            EditorWindow(self.root, path, self.process_next, profile_name=self.selected_profile.get())
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
            logo_path = os.path.join(os.path.dirname(__file__), "Intramaq-logo-mail.png")
            if os.path.exists(logo_path):
                pil_img = Image.open(logo_path)
                pil_img.thumbnail((450, 250))
                self.tk_img = ImageTk.PhotoImage(pil_img)
                tk.Label(self, image=self.tk_img, bg=COLORS["SURFACE"]).pack(expand=True)
            else:
                tk.Label(self, text="DIGITALIZADOR INTRAMAQ", font=FONTS["TITLE"], bg=COLORS["SURFACE"], fg=COLORS["TEXT"]).pack(expand=True)
        except: pass
        
        self.start_animation()

    def start_animation(self):
        # Fade In (0.1s)
        self.fade_in(0)

    def fade_in(self, alpha):
        alpha += 0.1
        if alpha >= 1.0:
            self.attributes("-alpha", 1.0)
            self.after(800, self.start_fade_out) # Hold 0.8s
        else:
            self.attributes("-alpha", alpha)
            self.after(20, lambda: self.fade_in(alpha))

    def start_fade_out(self):
        self.fade_out(1.0)

    def fade_out(self, alpha):
        alpha -= 0.1
        if alpha <= 0:
            self.destroy()
            self.on_complete()
        else:
            self.attributes("-alpha", alpha)
            self.after(20, lambda: self.fade_out(alpha))

def main():
    root = tk.Tk()
    root.withdraw() # Hide main window initially
    
    def launch_main():
        root.deiconify()
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
    logo_path = resource_path("Intramaq-logo-mail.png")
    # Also check if it exists in current dir as fallback for icon
    if not os.path.exists(logo_path):
         logo_path = "Intramaq-logo-mail.png"
         
    logo_exists = os.path.exists(logo_path)
    
    if logo_exists:
        try:
            # Set App Icon
            icon_img = ImageTk.PhotoImage(file=logo_path)
            root.iconphoto(True, icon_img)
        except: pass

        # time.sleep(0.5) # Removed to improve startup speed
        SplashScreen(root, launch_main)
    else:
        launch_main()
        
    root.mainloop()