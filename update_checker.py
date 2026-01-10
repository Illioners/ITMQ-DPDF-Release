"""
Update Checker Module for CLASSPDF
Handles version checking and update notifications
"""
import json
import urllib.request
import webbrowser
from tkinter import messagebox

APP_VERSION = "1.0.0"
VERSION_URL = "https://TU_USUARIO.github.io/CLASSPDF/version.json"  # Reemplaza TU_USUARIO

def check_for_updates(silent=False):
    """
    Check for updates from GitHub Pages.
    
    Args:
        silent: If True, only show message if update is available
    
    Returns:
        tuple: (has_update, update_data)
    """
    try:
        response = urllib.request.urlopen(VERSION_URL, timeout=5)
        data = json.loads(response.read().decode('utf-8'))
        
        remote_version = data.get("version", "0.0.0")
        
        # Simple version comparison (assumes semantic versioning)
        if compare_versions(remote_version, APP_VERSION) > 0:
            return True, data
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
                "Error de Conexión",
                f"No se pudo comprobar actualizaciones:\n{str(e)}"
            )
        return False, None

def compare_versions(v1, v2):
    """
    Compare two version strings.
    Returns: 1 if v1 > v2, -1 if v1 < v2, 0 if equal
    """
    def normalize(v):
        return [int(x) for x in v.split(".")]
    
    parts1 = normalize(v1)
    parts2 = normalize(v2)
    
    for i in range(max(len(parts1), len(parts2))):
        p1 = parts1[i] if i < len(parts1) else 0
        p2 = parts2[i] if i < len(parts2) else 0
        
        if p1 > p2:
            return 1
        elif p1 < p2:
            return -1
    
    return 0

def show_update_dialog(update_data):
    """Show update available dialog with changelog."""
    version = update_data.get("version", "Unknown")
    download_url = update_data.get("download_url", "")
    changelog = update_data.get("changelog", "No hay información de cambios.")
    
    message = f"¡Nueva versión disponible!\n\n"
    message += f"Versión actual: {APP_VERSION}\n"
    message += f"Nueva versión: {version}\n\n"
    message += f"Cambios:\n{changelog}\n\n"
    message += "¿Desea descargar la actualización?"
    
    if messagebox.askyesno("Actualización Disponible", message):
        webbrowser.open(download_url)

def auto_check_updates():
    """Automatically check for updates (silent mode)."""
    has_update, data = check_for_updates(silent=True)
    if has_update:
        show_update_dialog(data)
