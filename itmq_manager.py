"""
ITMQ Application Manager
========================
Comprehensive manager for ClasificadorPDF with update, repair, and reinstall capabilities.
"""

import os
import sys
import time
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
import json
from pathlib import Path

# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging():
    """Setup logging with rotation."""
    log_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'ITMQ', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'manager.log')
    
    handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    
    logger = logging.getLogger('ITMQManager')
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger

logger = setup_logging()

# ============================================================================
# CONFIGURATION
# ============================================================================

VERSION_URL = "https://raw.githubusercontent.com/Illioners/ITMQ-DPDF-Release/main/version.json"
CACHE_DIR = os.path.join(os.getenv('LOCALAPPDATA'), 'ITMQ', 'cache')
APP_DIR = os.path.join(os.getenv('LOCALAPPDATA'), 'ClasificadorPDF')
APP_EXE = os.path.join(APP_DIR, 'ClasificadorPDF.exe')

# Modern color scheme matching ClasificadorPDF
COLORS = {
    "BG": "#F5F2EB",
    "SURFACE": "#FFFFFF",
    "ACCENT": "#E67E22",
    "BLUE": "#3498DB",
    "GREEN": "#27AE60",
    "RED": "#E74C3C",
    "TEXT": "#2D3436",
    "TEXT_SECONDARY": "#636E72",
    "BORDER": "#DFE6E9"
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_installed_version():
    """Get the currently installed version of ClasificadorPDF."""
    try:
        if not os.path.exists(APP_EXE):
            return None
        # Try to read version from a version file if it exists
        version_file = os.path.join(APP_DIR, 'version.txt')
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                return f.read().strip()
        return "Unknown"
    except Exception as e:
        logger.error(f"Error getting installed version: {e}")
        return "Unknown"

def fetch_version_info():
    """Fetch the latest version information from GitHub."""
    try:
        with urllib.request.urlopen(VERSION_URL, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data
    except Exception as e:
        logger.error(f"Error fetching version info: {e}")
        return None

def calculate_sha256(file_path):
    """Calculate SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def is_app_running():
    """Check if ClasificadorPDF is currently running."""
    try:
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq ClasificadorPDF.exe'],
            capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        return 'ClasificadorPDF.exe' in result.stdout
    except:
        return False

def kill_app():
    """Force kill ClasificadorPDF if running."""
    try:
        subprocess.run(
            ['taskkill', '/F', '/IM', 'ClasificadorPDF.exe'],
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        time.sleep(1)
    except Exception as e:
        logger.error(f"Error killing app: {e}")

# ============================================================================
# APPLICATION MANAGER UI
# ============================================================================

class ApplicationManager(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("ITMQ Application Manager")
        self.geometry("600x500")
        self.configure(bg=COLORS["BG"])
        self.resizable(False, False)
        
        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.winfo_screenheight() // 2) - (500 // 2)
        self.geometry(f"+{x}+{y}")
        
        # State variables
        self.installed_version = get_installed_version()
        self.latest_version_info = None
        self.is_processing = False
        
        self.create_widgets()
        self.check_for_updates_async()
        
    def create_widgets(self):
        """Create all UI widgets."""
        # Header
        header = tk.Frame(self, bg=COLORS["ACCENT"], height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(
            header, text="ITMQ Application Manager",
            font=("Segoe UI Variable Display", 20, "bold"),
            bg=COLORS["ACCENT"], fg="white"
        ).pack(pady=25)
        
        # Main content area
        content = tk.Frame(self, bg=COLORS["BG"])
        content.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Status card
        status_card = tk.Frame(content, bg=COLORS["SURFACE"], relief="flat", bd=0)
        status_card.pack(fill="x", pady=(0, 15))
        
        # Status info
        info_frame = tk.Frame(status_card, bg=COLORS["SURFACE"])
        info_frame.pack(fill="x", padx=20, pady=15)
        
        # Installed version
        tk.Label(
            info_frame, text="Installed Version:",
            font=("Segoe UI Variable Text", 10),
            bg=COLORS["SURFACE"], fg=COLORS["TEXT_SECONDARY"]
        ).grid(row=0, column=0, sticky="w", pady=5)
        
        self.lbl_installed = tk.Label(
            info_frame, text=self.installed_version or "Not Installed",
            font=("Segoe UI Variable Display", 12, "bold"),
            bg=COLORS["SURFACE"], fg=COLORS["TEXT"]
        )
        self.lbl_installed.grid(row=0, column=1, sticky="e", padx=10)
        
        # Latest version
        tk.Label(
            info_frame, text="Latest Version:",
            font=("Segoe UI Variable Text", 10),
            bg=COLORS["SURFACE"], fg=COLORS["TEXT_SECONDARY"]
        ).grid(row=1, column=0, sticky="w", pady=5)
        
        self.lbl_latest = tk.Label(
            info_frame, text="Checking...",
            font=("Segoe UI Variable Display", 12, "bold"),
            bg=COLORS["SURFACE"], fg=COLORS["TEXT"]
        )
        self.lbl_latest.grid(row=1, column=1, sticky="e", padx=10)
        
        # Status
        tk.Label(
            info_frame, text="Status:",
            font=("Segoe UI Variable Text", 10),
            bg=COLORS["SURFACE"], fg=COLORS["TEXT_SECONDARY"]
        ).grid(row=2, column=0, sticky="w", pady=5)
        
        self.lbl_status = tk.Label(
            info_frame, text="Ready",
            font=("Segoe UI Variable Display", 12, "bold"),
            bg=COLORS["SURFACE"], fg=COLORS["GREEN"]
        )
        self.lbl_status.grid(row=2, column=1, sticky="e", padx=10)
        
        info_frame.grid_columnconfigure(1, weight=1)
        
        # Action buttons
        btn_frame = tk.Frame(content, bg=COLORS["BG"])
        btn_frame.pack(fill="x", pady=(0, 15))
        
        # Update button
        self.btn_update = self.create_button(
            btn_frame, "🔄 Update", COLORS["BLUE"],
            self.start_update, row=0, col=0
        )
        
        # Repair button
        self.btn_repair = self.create_button(
            btn_frame, "🔧 Repair", COLORS["ACCENT"],
            self.start_repair, row=0, col=1
        )
        
        # Reinstall button
        self.btn_reinstall = self.create_button(
            btn_frame, "📥 Reinstall", COLORS["RED"],
            self.start_reinstall, row=1, col=0
        )
        
        # Launch button
        self.btn_launch = self.create_button(
            btn_frame, "🚀 Launch App", COLORS["GREEN"],
            self.launch_app, row=1, col=1
        )
        
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)
        
        # Progress area
        progress_frame = tk.Frame(content, bg=COLORS["SURFACE"])
        progress_frame.pack(fill="both", expand=True)
        
        tk.Label(
            progress_frame, text="Activity Log",
            font=("Segoe UI Variable Display", 11, "bold"),
            bg=COLORS["SURFACE"], fg=COLORS["TEXT"]
        ).pack(anchor="w", padx=15, pady=(15, 5))
        
        # Progress bar
        self.progress = ttk.Progressbar(
            progress_frame, mode='indeterminate',
            length=560
        )
        self.progress.pack(padx=15, pady=5)
        
        # Log text
        log_container = tk.Frame(progress_frame, bg=COLORS["SURFACE"])
        log_container.pack(fill="both", expand=True, padx=15, pady=(5, 15))
        
        scrollbar = tk.Scrollbar(log_container)
        scrollbar.pack(side="right", fill="y")
        
        self.txt_log = tk.Text(
            log_container, height=8, wrap="word",
            font=("Consolas", 9),
            bg="#F8F9FA", fg=COLORS["TEXT"],
            relief="flat", bd=0,
            yscrollcommand=scrollbar.set
        )
        self.txt_log.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.txt_log.yview)
        
        self.log("Application Manager initialized")
        
    def create_button(self, parent, text, color, command, row, col):
        """Create a styled button."""
        btn = tk.Button(
            parent, text=text,
            font=("Segoe UI Variable Display", 11, "bold"),
            bg=color, fg="white",
            relief="flat", bd=0,
            cursor="hand2",
            command=command,
            padx=20, pady=12
        )
        btn.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
        
        # Hover effects
        btn.bind("<Enter>", lambda e: btn.config(bg=self.darken_color(color)))
        btn.bind("<Leave>", lambda e: btn.config(bg=color))
        
        return btn
    
    def darken_color(self, hex_color):
        """Darken a hex color by 10%."""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r, g, b = int(r * 0.9), int(g * 0.9), int(b * 0.9)
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def log(self, message):
        """Add a message to the log."""
        timestamp = time.strftime("%H:%M:%S")
        self.txt_log.insert("end", f"[{timestamp}] {message}\n")
        self.txt_log.see("end")
        logger.info(message)
    
    def set_processing(self, is_processing):
        """Enable/disable buttons during processing."""
        self.is_processing = is_processing
        state = "disabled" if is_processing else "normal"
        
        self.btn_update.config(state=state)
        self.btn_repair.config(state=state)
        self.btn_reinstall.config(state=state)
        self.btn_launch.config(state=state)
        
        if is_processing:
            self.progress.start(10)
        else:
            self.progress.stop()
    
    def update_status(self, text, color=None):
        """Update the status label."""
        self.lbl_status.config(text=text)
        if color:
            self.lbl_status.config(fg=color)
    
    # ========================================================================
    # UPDATE CHECK
    # ========================================================================
    
    def check_for_updates_async(self):
        """Check for updates in background."""
        threading.Thread(target=self.check_for_updates, daemon=True).start()
    
    def check_for_updates(self):
        """Check for available updates."""
        self.log("Checking for updates...")
        version_info = fetch_version_info()
        
        if version_info:
            self.latest_version_info = version_info
            latest_version = version_info.get('version', 'Unknown')
            self.lbl_latest.config(text=latest_version)
            
            if self.installed_version and self.installed_version != "Unknown":
                if latest_version != self.installed_version:
                    self.log(f"Update available: {latest_version}")
                    self.update_status("Update Available", COLORS["ACCENT"])
                else:
                    self.log("Application is up to date")
                    self.update_status("Up to Date", COLORS["GREEN"])
            else:
                self.log("Application not installed")
                self.update_status("Not Installed", COLORS["RED"])
        else:
            self.lbl_latest.config(text="Error")
            self.log("Failed to check for updates")
            self.update_status("Check Failed", COLORS["RED"])
    
    # ========================================================================
    # UPDATE OPERATION
    # ========================================================================
    
    def start_update(self):
        """Start the update process."""
        if self.is_processing:
            return
        
        if not self.latest_version_info:
            messagebox.showerror("Error", "No version information available")
            return
        
        if not self.installed_version or self.installed_version == "Unknown":
            messagebox.showinfo("Info", "Application not installed. Use Reinstall instead.")
            return
        
        if self.latest_version_info['version'] == self.installed_version:
            messagebox.showinfo("Info", "Application is already up to date")
            return
        
        self.set_processing(True)
        self.update_status("Updating...", COLORS["BLUE"])
        threading.Thread(target=self.perform_update, daemon=True).start()
    
    def perform_update(self):
        """Perform the actual update."""
        try:
            self.log("Starting update process...")
            
            # Check if app is running
            if is_app_running():
                self.log("Closing ClasificadorPDF...")
                kill_app()
                time.sleep(2)
            
            # Download update
            download_url = self.latest_version_info['download_url']
            sha256_expected = self.latest_version_info['sha256']
            
            self.log(f"Downloading from {download_url}...")
            temp_zip = os.path.join(CACHE_DIR, 'update.zip')
            os.makedirs(CACHE_DIR, exist_ok=True)
            
            urllib.request.urlretrieve(download_url, temp_zip)
            self.log("Download complete")
            
            # Verify hash
            self.log("Verifying file integrity...")
            sha256_actual = calculate_sha256(temp_zip)
            if sha256_actual.lower() != sha256_expected.lower():
                raise Exception("SHA256 mismatch - file corrupted")
            self.log("Verification successful")
            
            # Extract (skip manager and updater)
            self.log("Installing update...")
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    # Skip manager and updater to avoid access denied errors
                    if member.lower() in ['itmq-manager.exe', 'itmq-updater.exe']:
                        continue
                    zip_ref.extract(member, APP_DIR)
            
            # Save version
            with open(os.path.join(APP_DIR, 'version.txt'), 'w') as f:
                f.write(self.latest_version_info['version'])
            
            self.log("Update completed successfully!")
            self.installed_version = self.latest_version_info['version']
            self.lbl_installed.config(text=self.installed_version)
            self.update_status("Up to Date", COLORS["GREEN"])
            
            messagebox.showinfo("Success", "Update completed successfully!")
            
        except Exception as e:
            self.log(f"Update failed: {e}")
            messagebox.showerror("Error", f"Update failed: {e}")
            self.update_status("Update Failed", COLORS["RED"])
        finally:
            self.set_processing(False)
    
    # ========================================================================
    # REPAIR OPERATION
    # ========================================================================
    
    def start_repair(self):
        """Start the repair process."""
        if self.is_processing:
            return
        
        cached_file = os.path.join(CACHE_DIR, 'update.zip')
        if not os.path.exists(cached_file):
            messagebox.showinfo("Info", "No cached files available. Use Reinstall instead.")
            return
        
        if messagebox.askyesno("Confirm", "This will repair the installation using cached files. Continue?"):
            self.set_processing(True)
            self.update_status("Repairing...", COLORS["ACCENT"])
            threading.Thread(target=self.perform_repair, daemon=True).start()
    
    def perform_repair(self):
        """Perform repair from cached files."""
        try:
            self.log("Starting repair process...")
            
            if is_app_running():
                self.log("Closing ClasificadorPDF...")
                kill_app()
                time.sleep(2)
            
            cached_file = os.path.join(CACHE_DIR, 'update.zip')
            self.log("Extracting cached files...")
            
            with zipfile.ZipFile(cached_file, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    # Skip manager and updater to avoid access denied errors
                    if member.lower() in ['itmq-manager.exe', 'itmq-updater.exe']:
                        continue
                    zip_ref.extract(member, APP_DIR)
            
            self.log("Repair completed successfully!")
            self.update_status("Repaired", COLORS["GREEN"])
            messagebox.showinfo("Success", "Repair completed successfully!")
            
        except Exception as e:
            self.log(f"Repair failed: {e}")
            messagebox.showerror("Error", f"Repair failed: {e}")
            self.update_status("Repair Failed", COLORS["RED"])
        finally:
            self.set_processing(False)
    
    # ========================================================================
    # REINSTALL OPERATION
    # ========================================================================
    
    def start_reinstall(self):
        """Start the reinstall process."""
        if self.is_processing:
            return
        
        if not self.latest_version_info:
            messagebox.showerror("Error", "No version information available")
            return
        
        if messagebox.askyesno("Confirm", "This will download and reinstall the application. Continue?"):
            self.set_processing(True)
            self.update_status("Reinstalling...", COLORS["RED"])
            threading.Thread(target=self.perform_reinstall, daemon=True).start()
    
    def perform_reinstall(self):
        """Perform fresh reinstall."""
        try:
            self.log("Starting reinstall process...")
            
            if is_app_running():
                self.log("Closing ClasificadorPDF...")
                kill_app()
                time.sleep(2)
            
            # Download fresh copy
            download_url = self.latest_version_info['download_url']
            sha256_expected = self.latest_version_info['sha256']
            
            self.log(f"Downloading from {download_url}...")
            temp_zip = os.path.join(CACHE_DIR, 'update.zip')
            os.makedirs(CACHE_DIR, exist_ok=True)
            
            urllib.request.urlretrieve(download_url, temp_zip)
            self.log("Download complete")
            
            # Verify
            self.log("Verifying file integrity...")
            sha256_actual = calculate_sha256(temp_zip)
            if sha256_actual.lower() != sha256_expected.lower():
                raise Exception("SHA256 mismatch - file corrupted")
            self.log("Verification successful")
            
            # Clean install directory (except manager files)
            if os.path.exists(APP_DIR):
                self.log("Removing old installation...")
                for item in os.listdir(APP_DIR):
                    item_path = os.path.join(APP_DIR, item)
                    # Skip manager and updater to avoid access denied errors
                    if item.lower() in ['itmq-manager.exe', 'itmq-updater.exe']:
                        continue
                    try:
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                    except Exception as e:
                        self.log(f"Warning: Could not remove {item}: {e}")
            
            # Extract
            self.log("Installing application...")
            os.makedirs(APP_DIR, exist_ok=True)
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    # Skip manager and updater from zip to avoid conflicts
                    if member.lower() in ['itmq-manager.exe', 'itmq-updater.exe']:
                        continue
                    zip_ref.extract(member, APP_DIR)
            
            # Save version
            with open(os.path.join(APP_DIR, 'version.txt'), 'w') as f:
                f.write(self.latest_version_info['version'])
            
            self.log("Reinstall completed successfully!")
            self.installed_version = self.latest_version_info['version']
            self.lbl_installed.config(text=self.installed_version)
            self.update_status("Installed", COLORS["GREEN"])
            
            messagebox.showinfo("Success", "Reinstall completed successfully!")
            
        except Exception as e:
            self.log(f"Reinstall failed: {e}")
            messagebox.showerror("Error", f"Reinstall failed: {e}")
            self.update_status("Reinstall Failed", COLORS["RED"])
        finally:
            self.set_processing(False)
    
    # ========================================================================
    # LAUNCH APP
    # ========================================================================
    
    def launch_app(self):
        """Launch ClasificadorPDF."""
        if not os.path.exists(APP_EXE):
            messagebox.showerror("Error", "Application not installed")
            return
        
        try:
            self.log("Launching ClasificadorPDF...")
            subprocess.Popen([APP_EXE], creationflags=subprocess.CREATE_NO_WINDOW)
            self.log("Application launched")
            self.after(1000, self.destroy)  # Close manager after 1 second
        except Exception as e:
            self.log(f"Failed to launch: {e}")
            messagebox.showerror("Error", f"Failed to launch application: {e}")

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    try:
        app = ApplicationManager()
        app.mainloop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        messagebox.showerror("Fatal Error", f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
