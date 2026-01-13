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
        
        # Find version.json asset for detailed metadata
        version_data = {}
        for asset in release_data.get("assets", []):
            if asset.get("name") == "version.json":
                try:
                    v_url = asset.get("browser_download_url")
                    v_request = urllib.request.Request(v_url, headers={'User-Agent': 'CLASSPDF-Updater'})
                    v_response = urllib.request.urlopen(v_request, timeout=10)
                    version_data = json.loads(v_response.read().decode('utf-8'))
                except Exception as e:
                    print(f"Could not load version.json asset: {e}")
                break

        # Find download URL for ClasificadorPDF.exe
        download_url = ""
        for asset in release_data.get("assets", []):
            if asset.get("name") == "ClasificadorPDF.exe":
                download_url = asset.get("browser_download_url")
                break
        
        # Determine version and SHA256
        # Prioritize version.json, fallback to API/Body
        version = version_data.get("version", release_data.get("tag_name", "v0.0.0").lstrip('v'))
        sha256 = version_data.get("sha256", "")
        
        if not sha256:
            # Extract SHA256 from body using regex (fallback)
            sha_match = re.search(r'SHA256:\s*[`*]*([a-fA-F0-9]{64})[`*]*', body)
            if sha_match:
                sha256 = sha_match.group(1)
            else:
                hex_matches = re.findall(r'([a-fA-F0-9]{64})', body)
                if hex_matches:
                    sha256 = hex_matches[0]
        
        return {
            "version": version,
            "release_date": version_data.get("release_date", release_data.get("published_at", "")[:10]),
            "download_url": download_url,
            "sha256": sha256,
            "changelog": version_data.get("changelog", body),
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
        # Use LOCALAPPDATA for updates to avoid permission issues
        app_data_dir = os.path.join(os.getenv('LOCALAPPDATA', os.path.expanduser('~')), "ClasificadorPDF", "Updates")
        if not os.path.exists(app_data_dir):
            try:
                os.makedirs(app_data_dir)
            except OSError: pass
            
        temp_file = os.path.join(app_data_dir, "ClasificadorPDF_update.exe")
        
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

def verify_update(file_path, expected_hash):
    """Verify that the downloaded file matches the expected SHA256 hash"""
    if not expected_hash:
        return True, "Advertencia: No hay hash de verificación disponible."
    
    try:
        actual_hash = calculate_sha256(file_path)
        if actual_hash.lower() == expected_hash.lower():
            return True, "Verificación exitosa."
        else:
            return False, f"Error de integridad: El hash no coincide.\nEsperado: {expected_hash}\nObtenido: {actual_hash}"
    except Exception as e:
        return False, f"Error durante la verificación: {e}"

def install_update(downloaded_file, version):
    """
    Generate and launch a visible batch script to handle installation from a downloaded file.
    """
    try:
        if getattr(sys, 'frozen', False):
            current_exe = sys.executable
        else:
            messagebox.showwarning(
                "Modo Desarrollo",
                "La actualización automática solo funciona con el ejecutable compilado."
            )
            return False

        exe_dir = os.path.dirname(current_exe)
        exe_name = os.path.basename(current_exe)
        
        # Batch script content - No longer includes curl
        batch_content = f"""@echo off
title Actualizacion ClasificadorPDF - v{version}
color 0B
echo ============================================================
echo      ACTUALIZACION DE CLASIFICADOR PDF v{version}
echo ============================================================
echo.
echo Directorio: {exe_dir}
echo.

echo [1/3] Esperando a que el programa se cierre...
echo Cierre la aplicacion si aun esta abierta.
:wait_loop
tasklist /fi "imagename eq {exe_name}" | find /i "{exe_name}" > nul
if not errorlevel 1 (
    timeout /t 1 /nobreak > nul
    goto wait_loop
)

echo [2/3] Instalando archivos...
move /y "{downloaded_file}" "{current_exe}"
if errorlevel 1 (
    echo.
    echo [ERROR] No se pudo reemplazar el ejecutable.
    echo Intente ejecutar como administrador o verifique permisos.
    pause
    exit
)

echo [3/3] Actualizacion completada con exito.
echo.
echo Reiniciando ClasificadorPDF...
start "" "{current_exe}"
timeout /t 2 > nul
(goto) 2>nul & del "%~f0"
exit
"""
        
        batch_file = os.path.join(exe_dir, "updater_script.bat")
        with open(batch_file, "w", encoding='utf-8') as f:
            f.write(batch_content)
        
        # Launch CMD in a new visible window
        # /c cmd /k will keep it open if it errors (but we have pause)
        # We use 'start' to ensure it's a separate top-level window
        subprocess.Popen(f'start "Actualizacion ClasificadorPDF" cmd /c "{batch_file}"', shell=True)
        return True
        
    except Exception as e:
        messagebox.showerror("Error de Actualización", f"No se pudo iniciar el instalador:\n{str(e)}")
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
        """Perform download, verification and transition to installer"""
        def _bg_task():
            try:
                download_url = self.update_data.get("download_url")
                expected_sha = self.update_data.get("sha256")
                version = self.update_data.get("version", "Unknown")
                
                if not download_url:
                    self.after(0, lambda: messagebox.showerror("Error", "URL de descarga no disponible."))
                    self.after(0, self.destroy)
                    return
                
                # 1. Download
                success, result = download_update(download_url, self.update_progress)
                if not success:
                    self.after(0, lambda: messagebox.showerror("Error de Descarga", result))
                    self.after(0, self.destroy)
                    return
                
                downloaded_file = result
                
                # 2. Verify
                self.after(0, lambda: self.status_label.config(text="Verificando integridad..."))
                valid, msg = verify_update(downloaded_file, expected_sha)
                if not valid:
                    self.after(0, lambda: messagebox.showerror("Error de Integridad", msg))
                    # Cleanup failed download
                    try: os.remove(downloaded_file)
                    except: pass
                    self.after(0, self.destroy)
                    return
                
                # 3. Install
                self.after(0, lambda: self.status_label.config(text="Iniciando instalador..."))
                if install_update(downloaded_file, version):
                    # Small delay to ensure CMD window is visible before app exits
                    self.after(500, lambda: sys.exit(0))
                else:
                    self.after(0, self.destroy)
                    
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Error durante la actualización:\n{str(e)}"))
                self.after(0, self.destroy)

        import threading
        threading.Thread(target=_bg_task, daemon=True).start()

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
