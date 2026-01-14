
import os
import sys
import time
import argparse
import subprocess
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
from logging.handlers import RotatingFileHandler
import zipfile
import shutil
import hashlib

# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging():
    log_dir = os.path.join(os.getenv('LOCALAPPDATA', os.path.expanduser('~')), 'ClasificadorPDF', 'Logs')
    try:
        os.makedirs(log_dir, exist_ok=True)
    except:
        return logging.getLogger('itmq_updater')
    
    log_file = os.path.join(log_dir, 'itmq_updater.log')
    handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=2, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    log = logging.getLogger('itmq_updater')
    log.setLevel(logging.INFO)
    log.addHandler(handler)
    return log

logger = setup_logging()

# ============================================================================
# STYLING & CONFIG
# ============================================================================

COLORS = {
    "BG": "#F5F2EB",
    "SURFACE": "#FFFFFF",
    "ACCENT": "#E67E22",
    "TEXT": "#2D3436",
    "TEXT_SECONDARY": "#636E72"
}

class UpdaterUI(tk.Tk):
    def __init__(self, target_path, download_url, version, sha256, restart_args):
        super().__init__()
        self.target_path = os.path.abspath(target_path)
        self.download_url = download_url
        self.version = version
        self.sha256 = sha256
        self.restart_args = restart_args
        self.cancelled = False

        logger.info(f"Updater initialized. Target: {self.target_path}, Version: {self.version}")
        self.setup_window()
        self.create_widgets()
        
        # Start the update process automatically
        self.after(1000, self.start_update_process)

    def setup_window(self):
        self.title("Actualizando ClasificadorPDF")
        self.geometry("450x250")
        self.resizable(False, False)
        self.configure(bg=COLORS["BG"])
        
        # Topmost to ensure visibility during swap
        self.attributes("-topmost", True)
        
        # Center window
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"+{x}+{y}")

    def create_widgets(self):
        # Header
        header = tk.Frame(self, bg=COLORS["SURFACE"], height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(
            header, 
            text="ITMQ-Updater", 
            font=("Segoe UI", 14, "bold"), 
            bg=COLORS["SURFACE"], 
            fg=COLORS["ACCENT"]
        ).pack(side="left", padx=20)
        
        # Main Content
        content = tk.Frame(self, bg=COLORS["BG"], padx=30, pady=20)
        content.pack(fill="both", expand=True)

        tk.Label(
            content,
            text=f"Actualizando a la versión {self.version}",
            font=("Segoe UI", 12),
            bg=COLORS["BG"],
            fg=COLORS["TEXT"]
        ).pack(anchor="w", pady=(0, 20))

        self.status_label = tk.Label(
            content,
            text="Iniciando...",
            font=("Segoe UI", 9),
            bg=COLORS["BG"],
            fg=COLORS["TEXT_SECONDARY"]
        )
        self.status_label.pack(anchor="w", pady=(0, 5))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            content,
            variable=self.progress_var,
            maximum=100,
            length=390,
            mode='determinate'
        )
        self.progress_bar.pack(fill="x")

    def update_status(self, text):
        logger.info(f"Status update: {text}")
        self.status_label.config(text=text)
        self.update()

    def start_update_process(self):
        threading.Thread(target=self.run_update, daemon=True).start()

    def run_update(self):
        try:
            # 1. Wait for application to close
            self.update_status("Esperando cierre de la aplicación...")
            if not self.wait_for_app_close():
                 # Si tras esperar no cierra, intentamos forzar el cierre
                 self.update_status("Forzando cierre de la aplicación...")
                 self.force_kill_app()
                 # Dar un momento tras el kill
                 time.sleep(2)
                 if not self.wait_for_app_close():
                    logger.error("Application failed to close even after force kill")
                    raise Exception("No se pudo cerrar la aplicación. Por favor, ciérrela manualmente.")

            # 2. Download new version (ZIP)
            self.update_status("Descargando actualización (ZIP)...")
            temp_zip = self.download_file()
            if not temp_zip:
                logger.error("Download failed")
                return

            # 3. Verify Integrity
            if self.sha256:
                self.update_status("Verificando integridad...")
                if self.hash_file(temp_zip) != self.sha256:
                    logger.error("Hash verification failed")
                    raise Exception("La verificación de integridad (SHA256) falló. El archivo puede estar corrupto.")
            
            # 4. Extract and Replace
            self.update_status("Extrayendo e instalando archivos...")
            self.replace_directory(temp_zip)

            # 5. Success & Launch
            self.update_status("¡Actualización completada!")
            self.progress_var.set(100)
            time.sleep(1.5)
            self.launch_app()
            
            logger.info("Process finished successfully.")
            self.quit()

        except Exception as e:
            logger.error(f"Update failed: {e}", exc_info=True)
            messagebox.showerror("Error de Actualización", f"Ocurrió un error:\n{str(e)}")
            self.quit()

    def force_kill_app(self):
        """Attempts to kill the process by its filename"""
        try:
            filename = os.path.basename(self.target_path)
            logger.info(f"Attempting to force kill: {filename}")
            # Use taskkill on Windows
            result = subprocess.run(["taskkill", "/F", "/IM", filename, "/T"], capture_output=True, text=True)
            logger.info(f"Taskkill output: {result.stdout}")
            if result.stderr:
                logger.warning(f"Taskkill error output: {result.stderr}")
        except Exception as e:
            logger.warning(f"Failed to force kill {filename}: {e}")

    def wait_for_app_close(self):
        # Give it a moment to close nicely if it's just starting
        time.sleep(1)
        
        retries = 10 # 10 seconds wait
        while retries > 0:
            try:
                # Si el archivo no existe (raro), consideramos que está "cerrado"
                if not os.path.exists(self.target_path):
                    logger.info("Target file does not exist, assuming it's closed.")
                    return True
                    
                # Intentamos renombrar para verificar bloqueo
                test_name = self.target_path + ".test"
                if os.path.exists(test_name):
                    try:
                        os.remove(test_name)
                    except:
                        pass
                
                os.rename(self.target_path, test_name)
                # Volver a su sitio
                os.rename(test_name, self.target_path)
                logger.info("Target file is NOT locked.")
                return True
            except (IOError, OSError) as e:
                logger.info(f"Target is locked (Attempt {11-retries}): {e}")
                time.sleep(1)
                retries -= 1
        
        return False

    def download_file(self):
        try:
            logger.info(f"Starting download from: {self.download_url}")
            req = urllib.request.Request(
                self.download_url, 
                headers={'User-Agent': 'ITMQ-Updater'}
            )
            
            with urllib.request.urlopen(req, timeout=60) as response:
                total_size = int(response.headers.get('content-length', 0))
                temp_filename = self.target_path + ".update.zip"
                
                downloaded = 0
                chunk_size = 65536 # Larger buffer for ZIP
                
                with open(temp_filename, 'wb') as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            self.progress_var.set(percent)
                            
                logger.info(f"Download completed: {temp_filename} ({downloaded} bytes)")
                return temp_filename
                
        except Exception as e:
            logger.error(f"Download error: {e}")
            messagebox.showerror("Error de Descarga", f"No se pudo descargar la actualización:\n{e}")
            return None

    def hash_file(self, file_path):
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def replace_directory(self, temp_zip):
        """Extract ZIP content over the existing application directory."""
        try:
            logger.info("Replacing application directory...")
            app_dir = os.path.dirname(self.target_path)
            
            # 1. Create a temp extraction folder
            extract_dir = os.path.join(app_dir, "_new_files_temp")
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
            os.makedirs(extract_dir)

            # 2. Extract ZIP
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            logger.info(f"Extracted files to {extract_dir}")

            # 3. Move files one by one to overwrite
            # We skip the updater itself if it's in the same folder (it shouldn't be as it's running from temp usually)
            self_exe = os.path.basename(sys.argv[0])
            
            for item in os.listdir(extract_dir):
                if item == self_exe: continue
                
                s = os.path.join(extract_dir, item)
                d = os.path.join(app_dir, item)
                
                try:
                    if os.path.isdir(s):
                        if os.path.exists(d):
                            shutil.rmtree(d, ignore_errors=True)
                        shutil.move(s, d)
                    else:
                        # For files, try multiple times in case of locks
                        retries = 3
                        while retries > 0:
                            try:
                                if os.path.exists(d): os.remove(d)
                                shutil.move(s, d)
                                break
                            except Exception:
                                time.sleep(1)
                                retries -= 1
                except Exception as e:
                    logger.warning(f"Failed to move {item}: {e}")

            # 4. Post-replacement cleanup
            shutil.rmtree(extract_dir, ignore_errors=True)
            try:
                os.remove(temp_zip)
            except:
                pass
            
            # 5. Unblock all files
            self.unblock_directory(app_dir)
            
        except Exception as e:
            logger.error(f"Directory replacement failed: {e}")
            raise Exception(f"No se pudieron reemplazar los archivos: {e}")

    def unblock_directory(self, app_dir):
        """Unblock all files in the directory using PowerShell."""
        try:
            logger.info(f"Unblocking all files in: {app_dir}")
            ps_command = f"Get-ChildItem -Path '{app_dir}' -Recurse -File | Unblock-File -ErrorAction SilentlyContinue"
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=30
            )
            logger.info("Unblock-File finished.")
        except Exception as e:
            logger.warning(f"Unblock failed: {e}")

    def launch_app(self):
        try:
            logger.info(f"Launching app: {self.target_path} with args: {self.restart_args}")
            # Ensure path is quoted if it has spaces
            if os.path.exists(self.target_path):
                cmd = [self.target_path] + self.restart_args
                subprocess.Popen(cmd)
                self.cleanup()
            else:
                 logger.error(f"Target EXE not found after update: {self.target_path}")
                 messagebox.showerror("Error", "No se encontró el ejecutable principal después de la actualización.")
        except Exception as e:
            logger.error(f"Launch error: {e}")
            messagebox.showwarning("Advertencia", f"Actualización exitosa pero no se pudo reiniciar la app:\n{e}")

    def cleanup(self):
        """Self-delete the updater executable"""
        try:
            self_path = os.path.abspath(sys.argv[0])
            if getattr(sys, 'frozen', False):
                logger.info("Scheduling self-deletion...")
                cmd = f'ping 127.0.0.1 -n 3 > nul & del /F /Q "{self_path}"'
                subprocess.Popen(f'cmd /c {cmd}', shell=True)
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

def main():
    logger.info(f"--- UPDATER SESSION START --- Args: {sys.argv}")
    parser = argparse.ArgumentParser(description="ITMQ Updater")
    parser.add_argument("--target", required=True, help="Path to the executable to update")
    parser.add_argument("--url", required=True, help="Download URL for the new version")
    parser.add_argument("--version", required=True, help="New version number")
    parser.add_argument("--sha256", help="Expected SHA256 of the ZIP file")
    # Using REMAINDER to capture all subsequent args correctly
    parser.add_argument("--restart-args", nargs=argparse.REMAINDER, help="Arguments to pass to the app on restart")
    
    try:
        args = parser.parse_args()
    except Exception as e:
        logger.error(f"Argument parsing error: {e}")
        # Manual fallback if argparse fails on complex flags
        try:
             # Very basic fallback for common structure
             args = argparse.Namespace()
             args.target = sys.argv[sys.argv.index("--target") + 1]
             args.url = sys.argv[sys.argv.index("--url") + 1]
             args.version = sys.argv[sys.argv.index("--version") + 1]
             if "--restart-args" in sys.argv:
                 args.restart_args = sys.argv[sys.argv.index("--restart-args") + 1:]
             else:
                 args.restart_args = []
        except:
             sys.exit(1)

    # Clean up restart args if they contain the flag itself (happens with REMAINDER)
    if args.restart_args and args.restart_args[0] == "--restart-args":
        args.restart_args = args.restart_args[1:]

    # Check target dir
    target_dir = os.path.dirname(os.path.abspath(args.target))
    if not os.path.isdir(target_dir):
         logger.error(f"Target directory does not exist: {target_dir}")
         sys.exit(1)

    app = UpdaterUI(args.target, args.url, args.version, getattr(args, 'sha256', None), args.restart_args)
    app.mainloop()

if __name__ == "__main__":
    main()
