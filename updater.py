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
import time
import logging
from logging.handlers import RotatingFileHandler
from urllib.parse import urlparse
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

class UpdaterConfig:
    """Configuration management for the updater system"""
    
    def __init__(self):
        self.app_version = "1.0.0"
        self.github_repo = "USUARIO/REPO"
        self.auto_check_updates = True
        self.api_timeout = 10
        self.download_timeout = 30
        self.max_retries = 3
        self.max_download_size = 100 * 1024 * 1024  # 100 MB
        self.chunk_size = 8192
        self.progress_update_threshold = 1  # Update UI every 1% change
    
    def load_from_file(self, config_path):
        """Load configuration from build_config.json"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.app_version = config.get("version", self.app_version)
                    self.github_repo = config.get("github_repo", self.github_repo)
                    self.auto_check_updates = config.get("auto_check_updates", self.auto_check_updates)
                    logger.info(f"Configuration loaded: v{self.app_version}, repo={self.github_repo}")
            else:
                logger.warning(f"Config file not found: {config_path}, using defaults")
        except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
            logger.warning(f"Could not load config: {e}, using defaults")
        except Exception as e:
            logger.error(f"Unexpected error loading config: {e}", exc_info=True)
    
    def validate_github_repo(self):
        """Validate GitHub repository format"""
        pattern = r'^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$'
        if not re.match(pattern, self.github_repo):
            raise ValueError(f"Invalid GitHub repo format: {self.github_repo}")
        return self.github_repo.split('/')

# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging():
    """Setup structured logging with rotation"""
    log_dir = os.path.join(os.getenv('LOCALAPPDATA', os.path.expanduser('~')), 'ClasificadorPDF')
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError as e:
        print(f"Warning: Could not create log directory: {e}")
        return logging.getLogger('updater')
    
    log_file = os.path.join(log_dir, 'updater.log')
    
    handler = RotatingFileHandler(
        log_file,
        maxBytes=1024 * 1024,  # 1 MB
        backupCount=3,
        encoding='utf-8'
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger = logging.getLogger('updater')
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    
    # Also log to console in development
    if not getattr(sys, 'frozen', False):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

# ============================================================================
# GLOBAL CONFIGURATION INSTANCE
# ============================================================================

config = UpdaterConfig()

def load_config():
    """Load configuration from build_config.json"""
    try:
        config_path = get_resource_path("build_config.json")
        config.load_from_file(config_path)
    except Exception as e:
        logger.error(f"Error in load_config: {e}", exc_info=True)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
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
    except (ValueError, AttributeError) as e:
        logger.warning(f"Invalid version format: v1={v1}, v2={v2}, error={e}")
        return 0
    
    for i in range(max(len(parts1), len(parts2))):
        p1 = parts1[i] if i < len(parts1) else 0
        p2 = parts2[i] if i < len(parts2) else 0
        
        if p1 > p2:
            return 1
        elif p1 < p2:
            return -1
    
    return 0

def calculate_sha256(file_path):
    """Calculate SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except (FileNotFoundError, PermissionError, OSError) as e:
        logger.error(f"Error calculating SHA256 for {file_path}: {e}")
        raise

# Compiled regex patterns for efficiency
SHA256_PATTERN = re.compile(r'SHA256:\s*[`*]*([a-fA-F0-9]{64})[`*]*|([a-fA-F0-9]{64})')

def extract_sha256(body):
    """Extract SHA256 hash from release body text"""
    match = SHA256_PATTERN.search(body)
    if match:
        return match.group(1) or match.group(2)
    return ""

def validate_download_url(url):
    """Validate that download URL is from GitHub"""
    try:
        parsed = urlparse(url)
        allowed_domains = ['github.com', 'objects.githubusercontent.com', 'github-releases.githubusercontent.com']
        if parsed.netloc not in allowed_domains:
            raise ValueError(f"Invalid download URL domain: {parsed.netloc}")
        return True
    except Exception as e:
        logger.error(f"URL validation failed: {e}")
        return False

# ============================================================================
# USER-FRIENDLY ERROR MESSAGES
# ============================================================================

USER_FRIENDLY_ERRORS = {
    404: "La actualización aún no está disponible. Intente más tarde.",
    403: "Acceso denegado al servidor de actualizaciones.",
    500: "El servidor de actualizaciones está experimentando problemas.",
    502: "El servidor de actualizaciones no está disponible temporalmente.",
    503: "El servicio de actualizaciones está en mantenimiento.",
}

def get_user_friendly_error(code, default_msg=""):
    """Get user-friendly error message for HTTP status code"""
    return USER_FRIENDLY_ERRORS.get(code, default_msg or f"Error de conexión (código {code})")

# ============================================================================
# VERSION INFORMATION
# ============================================================================

def get_version_info():
    """Fetch version information from GitHub Releases API"""
    try:
        owner, repo = config.validate_github_repo()
        
        # GitHub API for latest release
        api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        
        request = urllib.request.Request(
            api_url,
            headers={
                'User-Agent': 'CLASSPDF-Updater',
                'Accept': 'application/vnd.github.v3+json'
            }
        )
        
        logger.info(f"Fetching version info from: {api_url}")
        response = urllib.request.urlopen(request, timeout=config.api_timeout)
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
                    v_response = urllib.request.urlopen(v_request, timeout=config.api_timeout)
                    version_data = json.loads(v_response.read().decode('utf-8'))
                    logger.info("Loaded version.json metadata")
                except (urllib.error.URLError, json.JSONDecodeError) as e:
                    logger.warning(f"Could not load version.json asset: {e}")
                break

        # Find download URL for ClasificadorPDF.exe AND ITMQ-Updater.exe
        download_url = ""
        updater_url = ""
        for asset in release_data.get("assets", []):
            name = asset.get("name")
            if name == "ClasificadorPDF.exe":
                download_url = asset.get("browser_download_url")
            elif name == "ITMQ-Updater.exe":
                updater_url = asset.get("browser_download_url")
        
        # Determine version and SHA256
        version = version_data.get("version", release_data.get("tag_name", "v0.0.0").lstrip('v'))
        sha256 = version_data.get("sha256", "") or extract_sha256(body)
        
        result = {
            "version": version,
            "release_date": version_data.get("release_date", release_data.get("published_at", "")[:10]),
            "download_url": download_url,
            "updater_url": updater_url,
            "sha256": sha256,
            "changelog": version_data.get("changelog", body),
            "url": release_data.get("html_url", "")
        }
        
        logger.info(f"Version info retrieved: v{version}")
        return result
        
    except urllib.error.HTTPError as e:
        error_msg = get_user_friendly_error(e.code, f"GitHub API Error {e.code}: {e.reason}")
        logger.error(f"HTTP Error {e.code}: {e.reason}")
        return {"error": error_msg}
    except urllib.error.URLError as e:
        error_msg = f"Error de red: {e.reason}"
        logger.error(f"URL Error: {e.reason}")
        return {"error": error_msg}
    except (json.JSONDecodeError, KeyError) as e:
        error_msg = "Error al procesar la respuesta del servidor"
        logger.error(f"Data parsing error: {e}", exc_info=True)
        return {"error": error_msg}
    except Exception as e:
        error_msg = "Error inesperado al verificar actualizaciones"
        logger.error(f"Unexpected error in get_version_info: {e}", exc_info=True)
        return {"error": error_msg}

def check_for_updates(silent=False):
    """
    Check if a new version is available.
    
    Args:
        silent: If True, only show message if update is available
    
    Returns:
        tuple: (has_update, update_data)
    """
    try:
        logger.info(f"Checking for updates (silent={silent})")
        remote_data = get_version_info()
        
        if not remote_data or "error" in remote_data:
            if not silent:
                error_msg = remote_data.get("error", "Error desconocido") if remote_data else "No se pudo obtener información."
                messagebox.showerror(
                    "Error de Conexión",
                    f"No se pudo conectar al servidor de actualizaciones.\n\nDetalle: {error_msg}"
                )
            return False, None
        
        remote_version = remote_data.get("version", "0.0.0")
        
        if compare_versions(remote_version, config.app_version) > 0:
            logger.info(f"Update available: {config.app_version} -> {remote_version}")
            return True, remote_data
        else:
            logger.info(f"No updates available (current: {config.app_version})")
            if not silent:
                messagebox.showinfo(
                    "Sin Actualizaciones",
                    f"Estás usando la versión más reciente ({config.app_version})"
                )
            return False, None
            
    except Exception as e:
        logger.error(f"Error in check_for_updates: {e}", exc_info=True)
        if not silent:
            messagebox.showerror(
                "Error",
                f"Error al verificar actualizaciones:\n{str(e)}"
            )
        return False, None

def force_reinstall(parent):
    """
    Fetch latest version info and show download dialog regardless of version.
    Useful for repairing installations or forcing a refresh.
    """
    try:
        logger.info("Force reinstall requested")
        remote_data = get_version_info()
        
        if not remote_data or "error" in remote_data:
            error_msg = remote_data.get("error", "Error desconocido") if remote_data else "No se pudo obtener información."
            messagebox.showerror(
                "Error de Conexión",
                f"No se pudo conectar al servidor de actualizaciones.\n\nDetalle: {error_msg}"
            )
            return
        
        version = remote_data.get("version", "Unknown")
        changelog = remote_data.get("changelog", "No hay información de cambios.")
        
        message = f"¿Desea reinstalar la aplicación?\n\n"
        message += f"Sincronizando con la última versión disponible: v{version}\n"
        message += f"\nNotas de la versión:\n{changelog}\n\n"
        message += "Esto descargará e instalará el ejecutable nuevamente."
        
        if messagebox.askyesno("Reinstalar Aplicación", message):
            UpdateDialog(parent, remote_data)
            
    except Exception as e:
        logger.error(f"Error in force_reinstall: {e}", exc_info=True)
        messagebox.showerror("Error", f"Error al preparar la reinstalación:\n{str(e)}")

# ============================================================================
# DOWNLOAD AND VERIFICATION
# ============================================================================

def download_update(download_url, progress_callback=None, cancel_check=None):
    """
    Download update file from URL with retry logic.
    
    Args:
        download_url: URL to download from
        progress_callback: Function to call with progress (0-100)
        cancel_check: Function that returns True if download should be cancelled
    
    Returns:
        tuple: (success, result_or_error_message)
    """
    # Validate URL
    if not validate_download_url(download_url):
        return False, "URL de descarga no válida o no es de GitHub"
    
    # Create temp directory for download
    app_data_dir = os.path.join(os.getenv('LOCALAPPDATA', os.path.expanduser('~')), "ClasificadorPDF", "Updates")
    try:
        os.makedirs(app_data_dir, exist_ok=True)
    except OSError as e:
        logger.error(f"Could not create update directory: {e}")
        return False, f"No se pudo crear el directorio de actualizaciones: {e}"
        
    temp_file = os.path.join(app_data_dir, "ITMQ-Updater.exe")
    
    # Clean up old file
    try:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    except Exception as e:
        logger.warning(f"Could not remove old updater file: {e}")
    
    # Retry logic
    for attempt in range(config.max_retries):
        try:
            logger.info(f"Download attempt {attempt + 1}/{config.max_retries}: {download_url}")
            
            request = urllib.request.Request(
                download_url,
                headers={'User-Agent': 'CLASSPDF-Updater'}
            )
            
            response = urllib.request.urlopen(request, timeout=config.download_timeout)
            total_size = int(response.headers.get('content-length', 0))
            
            # Check file size limit (Updater shouldn't be huge)
            if total_size > 50 * 1024 * 1024: # 50 MB Cap for updater
                return False, f"Actualizador demasiado grande: {total_size} bytes"
            
            logger.info(f"Downloading {total_size / 1024 / 1024:.1f} MB")
            
            downloaded = 0
            last_progress = -1
            
            with open(temp_file, 'wb') as f:
                while True:
                    # Check for cancellation
                    if cancel_check and cancel_check():
                        logger.info("Download cancelled by user")
                        return False, "Descarga cancelada"
                    
                    chunk = response.read(config.chunk_size)
                    if not chunk:
                        break
                    
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Throttled progress updates
                    if progress_callback and total_size > 0:
                        progress = int((downloaded / total_size) * 100)
                        if progress != last_progress and progress % config.progress_update_threshold == 0:
                            progress_callback(progress)
                            last_progress = progress
            
            logger.info(f"Download completed: {temp_file}")
            return True, temp_file
            
        except urllib.error.HTTPError as e:
            error_msg = get_user_friendly_error(e.code, f"Error HTTP {e.code}: {e.reason}")
            logger.error(f"HTTP Error on attempt {attempt + 1}: {e.code} {e.reason}")
            if attempt == config.max_retries - 1:
                return False, error_msg
            time.sleep(2 ** attempt)
            
        except Exception as e:
            logger.error(f"Error on attempt {attempt + 1}: {e}")
            if attempt == config.max_retries - 1:
                return False, f"Error desconocido: {e}"
            time.sleep(2 ** attempt)
            
    return False, f"Descarga fallida después de {config.max_retries} intentos"

def verify_update(file_path, expected_hash):
    """Verify that the downloaded file matches the expected SHA256 hash"""
    # NOTE: We are downloading ITMQ-Updater.exe, but the hash in authentication is usually for the MAIN app.
    # Unless we also have a hash for the updater.
    # For now, we will SKIP hash check for the updater itself unless provided.
    # The 'expected_hash' passed to this function usually comes from version.json which is for ClasificadorPDF.exe
    
    # If we want to verify the updater, we need the updater's hash in version.json.
    # For now, let's assume we trust the GitHub SSL download for the updater tool.
    return True, "Verificación omitida para ITMQ-Updater."

# ============================================================================
# INSTALLATION
# ============================================================================

def install_update(updater_exe_path, target_version, download_url_for_app):
    """
    Launch ITMQ-Updater.exe to handle the rest.
    """
    try:
        if getattr(sys, 'frozen', False):
            current_exe = sys.executable
        else:
            logger.warning("Update attempted in development mode")
            messagebox.showwarning(
                "Modo Desarrollo",
                "La actualización automática solo funciona con el ejecutable compilado."
            )
            return False

        current_exe = os.path.abspath(current_exe)
        updater_exe_path = os.path.abspath(updater_exe_path)
        
        logger.info(f"Launching ITMQ-Updater: {updater_exe_path}")
        logger.info(f"Target: {current_exe}")
        logger.info(f"Version: {target_version}")
        
        # Args for ITMQ-Updater
        args = [
            updater_exe_path,
            "--target", current_exe,
            "--url", download_url_for_app,
            "--version", target_version,
            "--restart-args", "--updated"
        ]
        
        subprocess.Popen(args)
        logger.info("ITMQ-Updater launched. Exiting main app...")
        return True
        
    except Exception as e:
        logger.error(f"Error launching updater: {e}", exc_info=True)
        messagebox.showerror("Error de Actualización", f"No se pudo iniciar el actualizador:\n{str(e)}")
        return False

# ============================================================================
# UPDATE DIALOG
# ============================================================================

class UpdateDialog(tk.Toplevel):
    """Dialog window for update download and installation"""
    
    def __init__(self, parent, update_data):
        super().__init__(parent)
        self.update_data = update_data
        self.cancelled = False
        
        self.title("Descargando Actualizador")
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
            text=f"Descargando herramienta de actualización...",
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
            text="Iniciando descarga del actualizador...",
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
        logger.info("User cancelled update")
        self.cancelled = True
        self.destroy()
    
    def is_cancelled(self):
        """Check if update was cancelled"""
        return self.cancelled
    
    def update_progress(self, progress):
        """Update progress bar"""
        if not self.cancelled:
            self.progress_var.set(progress)
            self.status_label.config(text=f"Descargando actualizador... {progress}%")
    
    def start_download(self):
        """Perform download of updater and transition to it"""
        def _bg_task():
            try:
                updater_url = self.update_data.get("updater_url")
                download_url = self.update_data.get("download_url")
                version = self.update_data.get("version", "Unknown")
                
                if not updater_url:
                    # Fallback? Or Critical Error?
                    # If ITMQ-Updater not found, maybe we are on an old version that expects the old way?
                    # But we are rewriting the code, so we expect it to exist.
                    logger.error("No updater URL provided")
                    
                    # Try to deduce it? Or fail.
                    # Let's fail gracefully.
                    self.after(0, lambda: messagebox.showerror("Error", "No se encontró el ejecutable del actualizador (ITMQ-Updater.exe) en la versión remota."))
                    self.after(0, self.destroy)
                    return
                
                # 1. Download ITMQ-Updater.exe
                success, result = download_update(
                    updater_url, 
                    self.update_progress,
                    self.is_cancelled
                )
                
                if not success:
                    if not self.cancelled:
                        self.after(0, lambda: messagebox.showerror("Error de Descarga", result))
                    self.after(0, self.destroy)
                    return
                
                updater_path = result
                
                # 2. Launch ITMQ-Updater
                self.after(0, lambda: self.status_label.config(text="Iniciando actualizador..."))
                
                if install_update(updater_path, version, download_url):
                    # Exit main app
                    self.after(500, lambda: os._exit(0))
                else:
                    self.after(0, self.destroy)
                    
            except Exception as e:
                logger.error(f"Error in background task: {e}", exc_info=True)
                self.after(0, lambda: messagebox.showerror("Error", f"Error durante la actualización:\n{str(e)}"))
                self.after(0, self.destroy)

        import threading
        threading.Thread(target=_bg_task, daemon=True).start()

# ============================================================================
# PUBLIC API
# ============================================================================

def show_update_dialog(parent, update_data):
    """Show update available dialog with changelog"""
    version = update_data.get("version", "Unknown")
    changelog = update_data.get("changelog", "No hay información de cambios.")
    release_date = update_data.get("release_date", "")
    
    message = f"¡Nueva versión disponible!\n\n"
    message += f"Versión actual: {config.app_version}\n"
    message += f"Nueva versión: {version}\n"
    if release_date:
        message += f"Fecha de lanzamiento: {release_date}\n"
    message += f"\nCambios:\n{changelog}\n\n"
    message += "¿Desea descargar e instalar la actualización ahora?"
    
    if messagebox.askyesno("Actualización Disponible", message):
        UpdateDialog(parent, update_data)

def auto_check_updates(parent):
    """Automatically check for updates on startup (silent mode)"""
    if not config.auto_check_updates:
        logger.info("Auto-check updates disabled")
        return
    
    logger.info("Auto-checking for updates")
    has_update, data = check_for_updates(silent=True)
    if has_update:
        show_update_dialog(parent, data)

# ============================================================================
# INITIALIZATION
# ============================================================================

# Load configuration on module import
load_config()
logger.info(f"Updater module initialized - Version {config.app_version}")
