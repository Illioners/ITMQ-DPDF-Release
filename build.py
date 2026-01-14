"""
Build Script for ClasificadorPDF (Final Optimizado)
"""
import json
import os
import hashlib
import sys
import shutil
import traceback  # Para ver errores detallados
from datetime import datetime

# ==========================================
# CONFIGURACIÓN Y UTILIDADES
# ==========================================

def get_abs_path(relative_path):
    """Obtiene la ruta absoluta basada en la ubicación del script."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

def force_clean_directories():
    """Elimina carpetas build y dist antiguas para evitar corrupción."""
    dirs_to_clean = ['build', 'dist']
    print("[INIT] Limpiando compilaciones anteriores...")
    for d in dirs_to_clean:
        path = get_abs_path(d)
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
                print(f"  - Eliminado: {d}/")
            except Exception as e:
                print(f"  [!] No se pudo eliminar {d}: {e}")

def check_dependencies():
    """Verifica que existan los archivos necesarios antes de empezar."""
    required_files = ['proglite.py'] 
    missing = [f for f in required_files if not os.path.exists(get_abs_path(f))]
    
    if missing:
        print(f"[FATAL] Faltan archivos fuente: {', '.join(missing)}")
        sys.exit(1)

    try:
        import PyInstaller
    except ImportError:
        print("[FATAL] PyInstaller no está instalado. Ejecuta: pip install pyinstaller")
        sys.exit(1)

def load_config():
    """Carga configuración."""
    config_path = get_abs_path('build_config.json')
    default_config = {"version": "1.0.0", "github_repo": "usuario/ClasificadorPDF"}

    if not os.path.exists(config_path):
        return default_config

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default_config

def update_version_file(config):
    """Actualiza version.json."""
    version = config.get('version', '1.0.0')
    repo = config.get('github_repo', 'repo')
    
    version_data = {
        "version": version,
        "release_date": datetime.now().strftime("%Y-%m-%d"),
        "download_url": f"https://github.com/{repo}/releases/download/v{version}/ClasificadorPDF.zip",
        "updater_url": f"https://github.com/{repo}/releases/download/v{version}/ITMQ-Updater.zip",
        "sha256": "",
        "changelog": "Actualización automática",
        "min_version": "1.0.0"
    }
    
    with open(get_abs_path('version.json'), 'w', encoding='utf-8') as f:
        json.dump(version_data, f, indent=2, ensure_ascii=False)
    
    return version_data

def calculate_sha256(file_path):
    if not os.path.exists(file_path): return None
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            sha.update(block)
    return sha.hexdigest()

# ==========================================
# PROCESOS DE COMPILACIÓN
# ==========================================

def build_executable(config):
    print("\n" + "="*50)
    print("[BUILD] Compilando ClasificadorPDF (App Principal)...")
    print("="*50)
    
    script_path = get_abs_path('proglite.py')
    manifest_path = get_abs_path("uac_manifest.xml")
    logo_path = get_abs_path("Intramaq-logo-mail.png")
    
    args = [
        script_path,
        '--name=ClasificadorPDF',
        '--onedir',
        '--windowed',
        '--clean',
        '--noconfirm',
        '--distpath=dist',
        '--workpath=build',
        f'--add-data={get_abs_path("version.json")};.',
        # Aseguramos que PyMuPDF (fitz) se incluya completamente
        '--hidden-import=fitz',
        '--collect-all=fitz', 
        '--hidden-import=PIL',
        '--collect-all=PIL'
    ]
    
    if os.path.exists(get_abs_path("build_config.json")):
        args.append(f'--add-data={get_abs_path("build_config.json")};.')
    if os.path.exists(logo_path):
        args.append(f'--add-data={logo_path};.')
        args.append(f'--icon={logo_path}') # Intenta usar el PNG como icono (PyInstaller a veces lo convierte solo)
    if os.path.exists(manifest_path):
        args.append(f'--manifest={manifest_path}')

    try:
        import PyInstaller.__main__
        PyInstaller.__main__.run(args)
        
        # Ruta esperada: dist/ClasificadorPDF/ClasificadorPDF.exe
        exe_path = get_abs_path(os.path.join('dist', 'ClasificadorPDF', 'ClasificadorPDF.exe'))
        
        if os.path.exists(exe_path):
            print(f"[OK] App compilada en: {exe_path}")
            return exe_path
        else:
            print(f"[ERROR] No se generó el EXE en: {exe_path}")
            return None
            
    except Exception:
        traceback.print_exc()
        return None

def build_updater():
    script_path = get_abs_path('itmq_updater.py')
    if not os.path.exists(script_path):
        print("\n[SKIP] itmq_updater.py no encontrado.")
        return None

    print("\n[BUILD] Compilando Updater...")
    args = [
        script_path,
        '--name=ITMQ-Updater',
        '--onedir',
        '--windowed',
        '--clean',
        '--noconfirm',
        '--distpath=dist',
        '--hidden-import=tkinter',
        '--hidden-import=urllib.request'
    ]
    
    try:
        import PyInstaller.__main__
        PyInstaller.__main__.run(args)
        return get_abs_path(os.path.join('dist', 'ITMQ-Updater', 'ITMQ-Updater.exe'))
    except Exception:
        traceback.print_exc()
        return None

def build_installer_inno(config):
    """Compila el instalador forzando rutas de salida."""
    iss_path = get_abs_path('installer.iss')
    if not os.path.exists(iss_path):
        print("\n[SKIP] installer.iss no encontrado.")
        return None
    
    # Buscar compilador Inno Setup
    iscc_exe = shutil.which("iscc") # Buscar en PATH
    if not iscc_exe:
        possible_paths = [
            r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            r"C:\Program Files\Inno Setup 6\ISCC.exe"
        ]
        for p in possible_paths:
            if os.path.exists(p):
                iscc_exe = p
                break
    
    if not iscc_exe:
        print("\n[SKIP] Inno Setup (ISCC.exe) no encontrado.")
        return None
        
    print("\n" + "="*50)
    print("[INSTALLER] Generando instalador con Inno Setup...")
    print("="*50)
    
    version = config.get('version', '1.0.0')
    installer_filename = f"ClasificadorPDF_Setup_v{version}"
    dist_path = get_abs_path('dist')
    
    # Comando ISCC con sobreescritura de variables
    # /O: Carpeta de salida
    # /F: Nombre del archivo de salida
    # /DMyAppVersion: Define la versión para usarla dentro del script .iss
    cmd = [
        iscc_exe,
        f"/O{dist_path}",
        f"/F{installer_filename}",
        f"/DMyAppVersion={version}",
        iss_path
    ]
    
    import subprocess
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            final_path = os.path.join(dist_path, installer_filename + ".exe")
            print(f"[OK] Instalador generado: {final_path}")
            return final_path
        else:
            print("[ERROR] Falló Inno Setup:")
            print(result.stdout)
            print(result.stderr)
            return None
    except Exception as e:
        print(f"[ERROR] Excepción ejecutando Inno Setup: {e}")
        return None

# ==========================================
# MAIN
# ==========================================

def main():
    print("=== BUILD SCRIPT: ClasificadorPDF ===")
    
    # 0. Limpieza inicial
    force_clean_directories()
    check_dependencies()
    
    config = load_config()
    print(f"Versión a compilar: {config.get('version')}")
    version_data = update_version_file(config)
    
    # 1. Compilar App
    exe_path = build_executable(config)
    if not exe_path:
        print("\n[FATAL] Falló la compilación principal.")
        sys.exit(1)
        
    # 2. Compilar Updater
    updater_path = build_updater()
    
    # 3. Empaquetar ZIPs
    print("\n[PACKAGING] Creando ZIPs...")
    
    # Preparar carpeta de App para Zipear
    app_folder = os.path.dirname(exe_path) # dist/ClasificadorPDF
    
    # Copiar extras
    for doc in ['LEEME.txt', 'INSTRUCCIONES.md', 'Reparar.bat', 'DesbloquearApp.bat', 'RepararAcceso.bat']:
        src = get_abs_path(doc)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(app_folder, doc))

    zip_base = get_abs_path(os.path.join('dist', 'ClasificadorPDF'))
    shutil.make_archive(zip_base, 'zip', app_folder)
    print(f"  -> ZIP App creado: {os.path.basename(zip_base)}.zip")
    
    # Hash
    sha = calculate_sha256(zip_base + ".zip")
    if sha:
        version_data['sha256'] = sha
        with open(get_abs_path('version.json'), 'w', encoding='utf-8') as f:
            json.dump(version_data, f, indent=2)
        print(f"  -> Hash SHA256 actualizado.")

    # Updater ZIP
    if updater_path:
        upd_folder = os.path.dirname(updater_path)
        upd_zip = get_abs_path(os.path.join('dist', 'ITMQ-Updater'))
        shutil.make_archive(upd_zip, 'zip', upd_folder)
        print(f"  -> ZIP Updater creado.")

    # 4. Instalador (Inno Setup)
    build_installer_inno(config)

    print("\n=== PROCESO FINALIZADO EXITOSAMENTE ===")

if __name__ == "__main__":
    main()