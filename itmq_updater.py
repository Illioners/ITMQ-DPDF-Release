
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
    def __init__(self, target_path, download_url, version, restart_args):
        super().__init__()
        self.target_path = os.path.abspath(target_path)
        self.download_url = download_url
        self.version = version
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
                 logger.error("Application failed to close or is locked")
                 raise Exception("La aplicación sigue abierta o el archivo está bloqueado.")

            # 2. Download new version
            self.update_status("Descargando actualización...")
            temp_file = self.download_file()
            if not temp_file:
                logger.error("Download failed")
                return

            # 3. Replace file
            self.update_status("Instalando archivos...")
            self.replace_file(temp_file)

            # 4. Success & Launch
            self.update_status("¡Actualización completada!")
            self.progress_var.set(100)
            time.sleep(1)
            self.launch_app()
            
            logger.info("Process finished successfully.")
            self.quit()

        except Exception as e:
            logger.error(f"Update failed: {e}", exc_info=True)
            messagebox.showerror("Error de Actualización", f"Ocurrió un error:\n{str(e)}")
            self.quit()

    def wait_for_app_close(self):
        # Give it a moment to close nicely
        time.sleep(2)
        
        retries = 15 # 15 seconds max
        while retries > 0:
            try:
                # Check if we can rename it. If we can rename it, it's NOT in use.
                # Renaming is more reliable than Opening for writing on Windows.
                test_name = self.target_path + ".test"
                if os.path.exists(test_name):
                    os.remove(test_name)
                
                os.rename(self.target_path, test_name)
                os.rename(test_name, self.target_path)
                return True
            except (IOError, OSError):
                logger.info(f"Target is locked, retry {retries}...")
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
            
            with urllib.request.urlopen(req, timeout=30) as response:
                total_size = int(response.headers.get('content-length', 0))
                temp_filename = self.target_path + ".tmp"
                
                downloaded = 0
                chunk_size = 8192
                
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

    def replace_file(self, temp_file):
        try:
            logger.info("Replacing target file...")
            # Windows might take a bit to release locks even after process exit
            retries = 5
            while retries > 0:
                try:
                    if os.path.exists(self.target_path):
                        os.remove(self.target_path)
                    os.rename(temp_file, self.target_path)
                    logger.info("Target replaced successfully.")
                    return
                except OSError as e:
                    logger.warning(f"Replace attempt failed ({retries}): {e}")
                    time.sleep(1)
                    retries -= 1
            
            raise Exception("No se pudo reemplazar el archivo tras varios intentos. Asegúrese de que no esté en uso.")
            
        except OSError as e:
            raise Exception(f"No se pudo reemplazar el archivo (Error: {e})")

    def launch_app(self):
        try:
            logger.info(f"Launching app: {self.target_path} with args: {self.restart_args}")
            # Ensure path is quoted if it has spaces
            cmd = [self.target_path] + self.restart_args
            subprocess.Popen(cmd)
            self.cleanup()
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
    logger.info("--- UPDATER SESSION START ---")
    parser = argparse.ArgumentParser(description="ITMQ Updater")
    parser.add_argument("--target", required=True, help="Path to the executable to update")
    parser.add_argument("--url", required=True, help="Download URL for the new version")
    parser.add_argument("--version", required=True, help="New version number")
    parser.add_argument("--restart-args", nargs="*", default=[], help="Arguments to pass to the app on restart")
    
    try:
        args = parser.parse_args()
    except Exception as e:
        logger.error(f"Argument parsing error: {e}")
        sys.exit(1)
    
    # Check target dir
    target_dir = os.path.dirname(os.path.abspath(args.target))
    if not os.path.isdir(target_dir):
         logger.error(f"Target directory does not exist: {target_dir}")
         sys.exit(1)

    app = UpdaterUI(args.target, args.url, args.version, args.restart_args)
    app.mainloop()

if __name__ == "__main__":
    main()
