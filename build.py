"""
Build Script for ClasificadorPDF (Reparado)
"""
import json
import os
import hashlib
import sys
import shutil
from datetime import datetime

# ==========================================
# CONFIGURACIÓN Y UTILIDADES
# ==========================================

def get_abs_path(relative_path):
    """Obtiene la ruta absoluta basada en la ubicación del script."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

def check_dependencies():
    """Verifica que existan los archivos necesarios antes de empezar."""
    required_files = ['proglite.py'] # Archivo principal
    missing = [f for f in required_files if not os.path.exists(get_abs_path(f))]
    
    if missing:
        print(f"[FATAL] Faltan archivos fuente necesarios: {', '.join(missing)}")
        print("Asegúrate de estar ejecutando build.py en la misma carpeta que proglite.py")
        sys.exit(1)

    try:
        import PyInstaller
    except ImportError:
        print("[FATAL] PyInstaller no está instalado. Ejecuta: pip install pyinstaller")
        sys.exit(1)

def load_config():
    """Carga o crea la configuración de compilación."""
    config_path = get_abs_path('build_config.json')
    
    # Configuración por defecto si no existe el archivo
    default_config = {
        "version": "1.0.0",
        "github_repo": "usuario/ClasificadorPDF" 
    }

    if not os.path.exists(config_path):
        print(f"[AVISO] No se encontró {config_path}, usando configuración por defecto.")
        return default_config

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] build_config.json corrupto: {e}")
        return default_config

def update_version_file(config):
    """Actualiza version.json."""
    version = config.get('version', '1.0.0')
    repo = config.get('github_repo', 'tu-repo')
    
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
    """Calcula SHA256."""
    if not os.path.exists(file_path):
        return None
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            sha.update(block)
    return sha.hexdigest()

# ==========================================
# PROCESOS DE COMPILACIÓN
# ==========================================

def build_executable(config):
    """Compila la aplicación principal."""
    print("\n" + "="*50)
    print("[BUILD] Compilando ClasificadorPDF...")
    print("="*50)
    
    script_path = get_abs_path('proglite.py')
    manifest_path = get_abs_path("uac_manifest.xml")
    logo_path = get_abs_path("Intramaq-logo-mail.png")
    
    # Argumentos para PyInstaller
    args = [
        script_path,
        '--name=ClasificadorPDF',
        '--onedir',   # Genera carpeta (importante para las rutas)
        '--windowed',
        '--clean',
        '--noconfirm',
        '--distpath=dist',
        '--workpath=build',
        # Incluir archivos de datos solo si existen
        f'--add-data={get_abs_path("version.json")};.',
    ]
    
    if os.path.exists(get_abs_path("build_config.json")):
        args.append(f'--add-data={get_abs_path("build_config.json")};.')
    
    if os.path.exists(logo_path):
        args.append(f'--add-data={logo_path};.')
        
    if os.path.exists(manifest_path):
        args.append(f'--manifest={manifest_path}')

    # Imports ocultos comunes
    args.extend([
        '--hidden-import=PIL',
        '--hidden-import=fitz',
        '--collect-all=fitz',
        '--collect-all=PIL'
    ])

    try:
        import PyInstaller.__main__
        PyInstaller.__main__.run(args)
        
        # --- CORRECCIÓN DE RUTA CRÍTICA ---
        # Con --onedir, el exe está en dist/NombreApp/NombreApp.exe
        exe_path = get_abs_path(os.path.join('dist', 'ClasificadorPDF', 'ClasificadorPDF.exe'))
        
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"[OK] Ejecutable creado exitosamente: {size_mb:.2f} MB")
            return exe_path
        else:
            print(f"[ERROR] No se encuentra el ejecutable en: {exe_path}")
            # Diagnóstico
            dist_dir = get_abs_path(os.path.join('dist', 'ClasificadorPDF'))
            if os.path.exists(dist_dir):
                print(f"Contenido de {dist_dir}: {os.listdir(dist_dir)}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Excepción en PyInstaller: {e}")
        return None

def build_updater():
    """Compila el actualizador."""
    script_path = get_abs_path('itmq_updater.py')
    if not os.path.exists(script_path):
        print("\n[SKIP] itmq_updater.py no encontrado, saltando compilación de updater.")
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
        return None

# ==========================================
# MAIN
# ==========================================

def main():
    print("INICIANDO PROCESO DE CONSTRUCCIÓN")
    check_dependencies()
    
    config = load_config()
    version_data = update_version_file(config)
    
    # 1. Compilar App Principal
    exe_path = build_executable(config)
    if not exe_path:
        print("\n[FALLO] La compilación principal falló. Revisa los errores arriba.")
        sys.exit(1)
        
    # 2. Compilar Updater (Opcional)
    updater_path = build_updater()
    
    # 3. Empaquetar ZIPs
    print("\n" + "="*50)
    print("[PACKAGING] Creando ZIPs para distribución...")
    print("="*50)
    
    # App ZIP
    app_folder = os.path.dirname(exe_path) # dist/ClasificadorPDF
    
    # Copiar documentación si existe
    for doc in ['LEEME.txt', 'INSTRUCCIONES.md', 'Reparar.bat']:
        src = get_abs_path(doc)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(app_folder, doc))

    zip_base = get_abs_path(os.path.join('dist', 'ClasificadorPDF'))
    shutil.make_archive(zip_base, 'zip', app_folder)
    print(f"[OK] ZIP App: {zip_base}.zip")
    
    # Calcular hash del ZIP final
    sha = calculate_sha256(zip_base + ".zip")
    if sha:
        version_data['sha256'] = sha
        with open(get_abs_path('version.json'), 'w', encoding='utf-8') as f:
            json.dump(version_data, f, indent=2)
        print(f"[INFO] SHA256 calculado: {sha}")

    # Updater ZIP
    if updater_path:
        upd_folder = os.path.dirname(updater_path)
        upd_zip = get_abs_path(os.path.join('dist', 'ITMQ-Updater'))
        shutil.make_archive(upd_zip, 'zip', upd_folder)
        print(f"[OK] ZIP Updater: {upd_zip}.zip")

    print("\n[LISTO] Compilación finalizada correctamente.")

if __name__ == "__main__":
    main()