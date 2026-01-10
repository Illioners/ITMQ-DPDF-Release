"""
Automatic Update System for CLASSPDF
Handles version checking, downloading, and installing updates from GitHub Releases
"""
import json
import urllib.request
import urllib.error
import os
import sys
import hashlib
import shutil
import subprocess
import tempfile
from tkinter import messagebox
import tkinter as tk
from tkinter import ttk

# Version will be loaded from build_config.json
APP_VERSION = "1.0.0"
GITHUB_REPO = "USUARIO/REPO"  # Will be loaded from config
AUTO_CHECK_UPDATES = True

def load_config():
    """Load configuration from build_config.json"""
    global APP_VERSION, GITHUB_REPO, AUTO_CHECK_UPDATES
    
    try:
        config_path = get_resource_path("build_config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                APP_VERSION = config.get("version", "1.0.0")
                GITHUB_REPO = config.get("github_repo", "USUARIO/REPO")
                AUTO_CHECK_UPDATES = config.get("auto_check_updates", True)
    except Exception as e:
        print(f"Error loading config: {e}")

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def compare_versions(v1, v2):
    """
    Compare two version strings.
    Returns: 1 if v1 > v2, -1 if v1 < v2, 0 if equal
    """
    def normalize(v):
        return [int(x) for x in v.split(".")]
    
    try:
        parts1 = normalize(v1)
        parts2 = normalize(v2)
    except ValueError:
        return 0
    
    for i in range(max(len(parts1), len(parts2))):
        p1 = parts1[i] if i < len(parts1) else 0
        p2 = parts2[i] if i < len(parts2) else 0
        
        if p1 > p2:
            return 1
        elif p1 < p2:
            return -1
    
    return 0

def get_version_info():
    """Fetch version information from GitHub"""
    try:
        # Construct GitHub Pages URL for version.json
        version_url = f"https://{GITHUB_REPO.split('/')[0]}.github.io/{GITHUB_REPO.split('/')[1]}/version.json"
        
        request = urllib.request.Request(
            version_url,
            headers={'User-Agent': 'CLASSPDF-Updater'}
        )
        
        response = urllib.request.urlopen(request, timeout=10)
        data = json.loads(response.read().decode('utf-8'))
        
        return data
    except urllib.error.URLError as e:
        print(f"Network error: {e}")
        return None
    except Exception as e:
        print(f"Error fetching version info: {e}")
        return None

def check_for_updates(silent=False):
    """
    Check if a new version is available.
    
    Args:
        silent: If True, only show message if update is available
    
    Returns:
        tuple: (has_update, update_data)
    """
    try:
        remote_data = get_version_info()
        
        if not remote_data:
            if not silent:
                messagebox.showerror(
                    "Error de Conexión",
                    "No se pudo conectar al servidor de actualizaciones."
                )
            return False, None
        
        remote_version = remote_data.get("version", "0.0.0")
        
        if compare_versions(remote_version, APP_VERSION) > 0:
            return True, remote_data
        else:
            if not silent:
                messagebox.showinfo(
                    "Sin Actualizaciones",
                    f"Estás usando la versión más reciente ({APP_VERSION})"
                )
            return False, None
            
    except Exception as e:
        if not silent:
            messagebox.showerror(
                "Error",
                f"Error al verificar actualizaciones:\n{str(e)}"
            )
        return False, None

def calculate_sha256(file_path):
    """Calculate SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def download_update(download_url, progress_callback=None):
    """
    Download update file from URL.
    
    Args:
        download_url: URL to download from
        progress_callback: Function to call with progress (0-100)
    
    Returns:
        Path to downloaded file or None if failed
    """
    try:
        # Create temp directory for download
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, "ClasificadorPDF_update.exe")
        
        # Download with progress
        request = urllib.request.Request(
            download_url,
            headers={'User-Agent': 'CLASSPDF-Updater'}
        )
        
        response = urllib.request.urlopen(request, timeout=30)
        total_size = int(response.headers.get('content-length', 0))
        
        downloaded = 0
        with open(temp_file, 'wb') as f:
            while True:
                chunk = response.read(8192)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                
                if progress_callback and total_size > 0:
                    progress = int((downloaded / total_size) * 100)
                    progress_callback(progress)
        
        return temp_file
        
    except Exception as e:
        print(f"Download error: {e}")
        return None

def install_update(update_file, expected_sha256=None):
    """
    Install the downloaded update.
    
    Args:
        update_file: Path to the downloaded update file
        expected_sha256: Expected SHA256 hash (optional)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Verify SHA256 if provided
        if expected_sha256:
            actual_sha256 = calculate_sha256(update_file)
            if actual_sha256.lower() != expected_sha256.lower():
                messagebox.showerror(
                    "Error de Verificación",
                    "El archivo descargado está corrupto o ha sido modificado.\nLa actualización ha sido cancelada."
                )
                return False
        
        # Get current executable path
        if getattr(sys, 'frozen', False):
            current_exe = sys.executable
        else:
            # Running from script, can't update
            messagebox.showwarning(
                "Modo Desarrollo",
                "La actualización automática solo funciona con el ejecutable compilado."
            )
            return False
        
        # Create backup
        backup_path = current_exe + ".backup"
        try:
            shutil.copy2(current_exe, backup_path)
        except Exception as e:
            print(f"Backup creation failed: {e}")
        
        # Create update script
        update_script = os.path.join(tempfile.gettempdir(), "update_classpdf.bat")
        
        with open(update_script, 'w') as f:
            f.write(f"""@echo off
timeout /t 2 /nobreak > nul
del /f /q "{current_exe}"
move /y "{update_file}" "{current_exe}"
start "" "{current_exe}"
del /f /q "{backup_path}"
del /f /q "%~f0"
""")
        
        # Execute update script and exit
        subprocess.Popen(update_script, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        
        return True
        
    except Exception as e:
        messagebox.showerror(
            "Error de Instalación",
            f"No se pudo instalar la actualización:\n{str(e)}"
        )
        return False

class UpdateDialog(tk.Toplevel):
    """Dialog window for update download and installation"""
    
    def __init__(self, parent, update_data):
        super().__init__(parent)
        self.update_data = update_data
        self.cancelled = False
        
        self.title("Descargando Actualización")
        self.geometry("500x200")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.winfo_screenheight() // 2) - (200 // 2)
        self.geometry(f"500x200+{x}+{y}")
        
        # UI Elements
        tk.Label(
            self,
            text=f"Descargando versión {update_data.get('version', 'Unknown')}...",
            font=("Segoe UI", 12, "bold")
        ).pack(pady=20)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self,
            variable=self.progress_var,
            maximum=100,
            length=400,
            mode='determinate'
        )
        self.progress_bar.pack(pady=10)
        
        self.status_label = tk.Label(
            self,
            text="Iniciando descarga...",
            font=("Segoe UI", 9)
        )
        self.status_label.pack(pady=5)
        
        self.cancel_btn = tk.Button(
            self,
            text="Cancelar",
            command=self.cancel,
            width=15
        )
        self.cancel_btn.pack(pady=10)
        
        # Start download
        self.after(100, self.start_download)
    
    def cancel(self):
        """Cancel the update"""
        self.cancelled = True
        self.destroy()
    
    def update_progress(self, progress):
        """Update progress bar"""
        if not self.cancelled:
            self.progress_var.set(progress)
            self.status_label.config(text=f"Descargando... {progress}%")
    
    def start_download(self):
        """Start the download process"""
        import threading
        
        def download_thread():
            try:
                download_url = self.update_data.get("download_url")
                expected_sha256 = self.update_data.get("sha256")
                
                if not download_url:
                    self.after(0, lambda: messagebox.showerror(
                        "Error",
                        "URL de descarga no disponible."
                    ))
                    self.after(0, self.destroy)
                    return
                
                # Download
                self.after(0, lambda: self.status_label.config(text="Descargando actualización..."))
                update_file = download_update(download_url, self.update_progress)
                
                if not update_file or self.cancelled:
                    self.after(0, self.destroy)
                    return
                
                # Install
                self.after(0, lambda: self.status_label.config(text="Instalando actualización..."))
                self.after(0, lambda: self.progress_var.set(100))
                
                if install_update(update_file, expected_sha256):
                    # Success - app will restart via update script
                    self.after(0, lambda: messagebox.showinfo(
                        "Actualización Completa",
                        "La aplicación se reiniciará para completar la actualización."
                    ))
                    self.after(0, lambda: sys.exit(0))
                else:
                    self.after(0, self.destroy)
                    
            except Exception as e:
                self.after(0, lambda: messagebox.showerror(
                    "Error",
                    f"Error durante la actualización:\n{str(e)}"
                ))
                self.after(0, self.destroy)
        
        threading.Thread(target=download_thread, daemon=True).start()

def show_update_dialog(parent, update_data):
    """Show update available dialog with changelog"""
    version = update_data.get("version", "Unknown")
    changelog = update_data.get("changelog", "No hay información de cambios.")
    release_date = update_data.get("release_date", "")
    
    message = f"¡Nueva versión disponible!\n\n"
    message += f"Versión actual: {APP_VERSION}\n"
    message += f"Nueva versión: {version}\n"
    if release_date:
        message += f"Fecha de lanzamiento: {release_date}\n"
    message += f"\nCambios:\n{changelog}\n\n"
    message += "¿Desea descargar e instalar la actualización ahora?"
    
    if messagebox.askyesno("Actualización Disponible", message):
        # Show download dialog
        UpdateDialog(parent, update_data)

def auto_check_updates(parent):
    """Automatically check for updates on startup (silent mode)"""
    if not AUTO_CHECK_UPDATES:
        return
    
    has_update, data = check_for_updates(silent=True)
    if has_update:
        show_update_dialog(parent, data)

# Load configuration on module import
load_config()
