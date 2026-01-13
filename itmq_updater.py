
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
        self.target_path = target_path
        self.download_url = download_url
        self.version = version
        self.restart_args = restart_args
        self.cancelled = False

        self.setup_window()
        self.create_widgets()
        
        # Start the update process automatically
        self.after(1000, self.start_update_process)

    def setup_window(self):
        self.title("Actualizando ClasificadorPDF")
        self.geometry("450x250")
        self.resizable(False, False)
        self.configure(bg=COLORS["BG"])
        
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
        self.status_label.config(text=text)
        self.update()

    def start_update_process(self):
        threading.Thread(target=self.run_update, daemon=True).start()

    def run_update(self):
        try:
            # 1. Wait for application to close
            self.update_status("Esperando cierre de la aplicación...")
            self.wait_for_app_close()

            # 2. Download new version
            self.update_status("Descargando actualización...")
            temp_file = self.download_file()
            if not temp_file:
                return

            # 3. Replace file
            self.update_status("Instalando archivos...")
            self.replace_file(temp_file)

            # 4. Success & Launch
            self.update_status("¡Actualización completada!")
            self.progress_var.set(100)
            time.sleep(1)
            self.launch_app()
            
            self.quit()

        except Exception as e:
            messagebox.showerror("Error de Actualización", f"Ocurrió un error:\n{str(e)}")
            self.quit()

    def wait_for_app_close(self):
        filename = os.path.basename(self.target_path)
        # Give it a moment to close nicely
        time.sleep(2)
        
        retries = 30 # 30 seconds max
        while retries > 0:
            try:
                # Try to open the file in append mode to check if it's locked
                # This is a simple cross-platform way to check file application ownership/lock
                with open(self.target_path, 'a+'):
                    pass
                break # If we can open it, it's likely closed
            except IOError:
                # File is locked, wait
                time.sleep(1)
                retries -= 1
        
        if retries == 0:
            # Try to force kill if still running? Or just fail?
            # For safety, let's ask user or fail. 
            # Ideally we'd use psutil but standard lib only here.
            pass

    def download_file(self):
        try:
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
                            
                return temp_filename
                
        except Exception as e:
            messagebox.showerror("Error de Descarga", f"No se pudo descargar la actualización:\n{e}")
            return None

    def replace_file(self, temp_file):
        try:
            # Backup current? Optional.
            # Replace
            if os.path.exists(self.target_path):
                os.remove(self.target_path)
            os.rename(temp_file, self.target_path)
        except OSError as e:
            raise Exception(f"No se pudo reemplazar el archivo (Error: {e})")

    def launch_app(self):
        try:
            subprocess.Popen([self.target_path] + self.restart_args)
            self.cleanup()
        except Exception as e:
            messagebox.showwarning("Advertencia", f"Actualización exitosa pero no se pudo reiniciar la app:\n{e}")

    def cleanup(self):
        """Self-delete the updater executable"""
        try:
            self_path = os.path.abspath(sys.argv[0])
            # Only self-delete if frozen (running as exe)
            if getattr(sys, 'frozen', False):
                # Use a separate process to delete this file after it exits
                # ping is used as a delay
                cmd = f'ping 127.0.0.1 -n 3 > nul & del "{self_path}"'
                subprocess.Popen(f'cmd /c {cmd}', shell=True)
        except Exception as e:
            print(f"Cleanup error: {e}")

def main():
    parser = argparse.ArgumentParser(description="ITMQ Updater")
    parser.add_argument("--target", required=True, help="Path to the executable to update")
    parser.add_argument("--url", required=True, help="Download URL for the new version")
    parser.add_argument("--version", required=True, help="New version number")
    parser.add_argument("--restart-args", nargs="*", default=[], help="Arguments to pass to the app on restart")
    
    args = parser.parse_args()
    
    # Need target path to exist ideally, or at least the dir
    if not os.path.isdir(os.path.dirname(os.path.abspath(args.target))):
         print(f"Error: Target directory does not exist: {args.target}")
         sys.exit(1)

    app = UpdaterUI(args.target, args.url, args.version, args.restart_args)
    app.mainloop()

if __name__ == "__main__":
    main()
