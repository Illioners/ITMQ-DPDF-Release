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
import re
from datetime import datetime

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
    """Fetch version information from GitHub Releases API"""
    try:
        parts = GITHUB_REPO.split('/')
        if len(parts) < 2:
            return None
            
        owner = parts[0]
        repo = parts[1]
        
        # GitHub API for latest release
        api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        
        request = urllib.request.Request(
            api_url,
            headers={
                'User-Agent': 'CLASSPDF-Updater',
                'Accept': 'application/vnd.github.v3+json'
            }
        )
        
        response = urllib.request.urlopen(request, timeout=10)
        release_data = json.loads(response.read().decode('utf-8'))
        
        # Map API response to our internal format
        version = release_data.get("tag_name", "v0.0.0").lstrip('v')
        body = release_data.get("body", "")
        
        # Find download URL for ClasificadorPDF.exe
        download_url = ""
        for asset in release_data.get("assets", []):
            if asset.get("name") == "ClasificadorPDF.exe":
                download_url = asset.get("browser_download_url")
                break
        
        # Extract SHA256 from body using regex
        # Pattern looks for "SHA256: `hash`" or "SHA256**: `hash`" or just the 64-char hex string
        sha256 = ""
        sha_match = re.search(r'SHA256:\s*[`*]*([a-fA-F0-9]{64})[`*]*', body)
        if sha_match:
            sha256 = sha_match.group(1)
        else:
            # Fallback: look for any 64-char hex string
            hex_matches = re.findall(r'([a-fA-F0-9]{64})', body)
            if hex_matches:
                sha256 = hex_matches[0]
        
        return {
            "version": version,
            "release_date": release_data.get("published_at", "")[:10],
            "download_url": download_url,
            "sha256": sha256,
            "changelog": body,
            "url": release_data.get("html_url", "")
        }
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        return {"error": f"GitHub API Error {e.code}: {e.reason}"}
    except Exception as e:
        print(f"Error fetching version info: {e}")
        return {"error": str(e)}

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
        
        if not remote_data or "error" in remote_data:
            if not silent:
                error_msg = remote_data.get("error", "Error desconocido") if remote_data else "No se pudo obtener información."
                url_msg = f"\nURL: {remote_data.get('url', '')}" if remote_data and 'url' in remote_data else ""
                messagebox.showerror(
                    "Error de Conexión",
                    f"No se pudo conectar al servidor de actualizaciones.\n\nDetalle: {error_msg}{url_msg}"
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
        tuple: (success, result_or_error_message)
    """
    try:
        # Create temp directory for download
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, "ClasificadorPDF_update.exe")
        
        # Ensure we can write to the file
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception as e:
            return False, f"No se pudo limpiar el archivo temporal: {e}"
        
        # Download with progress
        request = urllib.request.Request(
            download_url,
            headers={'User-Agent': 'CLASSPDF-Updater'}
        )
        
        try:
            response = urllib.request.urlopen(request, timeout=30)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False, "Error 404: El archivo de actualización no se encuentra en el servidor. Puede que GitHub aún esté procesando el release."
            return False, f"Error HTTP {e.code}: {e.reason}"
        except urllib.error.URLError as e:
            return False, f"Error de red: {e.reason}"
            
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
        
        return True, temp_file
        
    except Exception as e:
        print(f"Download error: {e}")
        return False, str(e)

def install_update(update_file, expected_sha256=None):
    """
    Verify and install update by replacing the current executable.
    
    Returns:
        bool: True if successful
    """
    try:
        # 1. Verify SHA256
        if expected_sha256:
            print("[INFO] Verificando integridad del archivo...")
            actual_sha256 = calculate_sha256(update_file)
            
            if actual_sha256.lower() != expected_sha256.lower():
                messagebox.showerror(
                    "Error de Integridad",
                    f"El archivo descargado está corrupto o no es válido.\n\n"
                    f"Esperado: {expected_sha256[:10]}...\n"
                    f"Obtenido: {actual_sha256[:10]}..."
                )
                return False
            print("[SUCCESS] Verificación SHA256 exitosa.")

        # 2. Get current executable path
        if getattr(sys, 'frozen', False):
            current_exe = sys.executable
        else:
            messagebox.showwarning(
                "Modo Desarrollo",
                "La actualización automática solo funciona con el ejecutable compilado."
            )
            return False

        # 3. Create batch script to replace the file after exit
        backup_exe = current_exe + ".bak"
        
        # We'll use a slightly more robust batch script
        batch_content = f"""@echo off
setlocal
echo Finalizando para actualizar...
timeout /t 2 /nobreak > nul

:retry
del /f /q "{current_exe}"
if exist "{current_exe}" (
    echo Esperando a que el proceso se cierre...
    timeout /t 1 /nobreak > nul
    goto retry
)

copy /y "{update_file}" "{current_exe}"
if errorlevel 1 (
    echo ERROR: No se pudo copiar el nuevo archivo.
    pause
    exit
)

del /f /q "{update_file}"
start "" "{current_exe}"
del /f /q "{backup_exe}"
del "%~f0"
"""
        
        batch_file = os.path.join(tempfile.gettempdir(), "update_helper.bat")
        with open(batch_file, "w") as f:
            f.write(batch_content)
        
        # 4. Launch batch script and exit
        subprocess.Popen([batch_file], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
        return True
        
    except Exception as e:
        messagebox.showerror("Error de Instalación", f"No se pudo preparar la instalación:\n{str(e)}")
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
                success, result = download_update(download_url, self.update_progress)
                
                if not success:
                    if not self.cancelled:
                        self.after(0, lambda r=result: messagebox.showerror(
                            "Error de Descarga",
                            f"No se pudo descargar la actualización:\n\n{r}"
                        ))
                    self.after(0, self.destroy)
                    return
                
                if self.cancelled:
                    self.after(0, self.destroy)
                    return

                update_file = result
                
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
