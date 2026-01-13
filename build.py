"""
Build Script for ClasificadorPDF
Compiles both the main application and the updater using PyInstaller.
No digital signature - executables are distributed unsigned.
"""
import json
import os
import hashlib
import sys
from datetime import datetime

def get_abs_path(relative_path):
    """Convert relative path to absolute path based on script location."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

def load_config():
    """Load build configuration from build_config.json."""
    config_path = get_abs_path('build_config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] No se encontró {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Error al leer build_config.json: {e}")
        sys.exit(1)

def update_version_file(config):
    """Create/update version.json with current build information."""
    version = config['version']
    repo = config['github_repo']
    
    version_data = {
        "version": version,
        "release_date": datetime.now().strftime("%Y-%m-%d"),
        "download_url": f"https://github.com/{repo}/releases/download/v{version}/ClasificadorPDF.exe",
        "sha256": "",  # Will be updated after build
        "changelog": "- Eliminada firma digital\n- Optimización del proceso de compilación\n- Limpieza de archivos innecesarios",
        "min_version": "1.0.0"
    }
    
    version_path = get_abs_path('version.json')
    with open(version_path, 'w', encoding='utf-8') as f:
        json.dump(version_data, f, indent=2, ensure_ascii=False)
    
    print(f"[INFO] version.json actualizado para v{version}")
    return version_data

def calculate_sha256(file_path):
    """Calculate SHA256 hash of a file."""
    if not os.path.exists(file_path):
        print(f"[ERROR] Archivo no encontrado: {file_path}")
        return None
    
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def build_executable(config):
    """Build the main application executable using PyInstaller."""
    print("\n" + "="*50)
    print("[BUILD] Compilando ClasificadorPDF.exe...")
    print("="*50)
    
    script_path = get_abs_path('proglite.py')
    manifest_path = get_abs_path("uac_manifest.xml")
    
    # PyInstaller arguments for main application
    args_main = [
        script_path,
        '--name=ClasificadorPDF',
        '--onefile',
        '--windowed',
        f'--add-data={get_abs_path("Intramaq-logo-mail.png")};.',
        f'--add-data={get_abs_path("version.json")};.',
        f'--add-data={get_abs_path("build_config.json")};.',
        '--clean',
        '--noconfirm',
        '--distpath=dist',
        '--workpath=build',
        '--hidden-import=PIL',
        '--hidden-import=fitz',
        '--collect-all=fitz',
        '--collect-all=PIL',
        f'--manifest={manifest_path}' if os.path.exists(manifest_path) else ''
    ]
    # Remove empty strings from args
    args_main = [a for a in args_main if a]
    
    try:
        import PyInstaller.__main__
        PyInstaller.__main__.run(args_main)
        
        exe_path = get_abs_path(os.path.join('dist', 'ClasificadorPDF.exe'))
        
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"[OK] ClasificadorPDF.exe generado ({size_mb:.2f} MB)")
            return exe_path
        else:
            print("[ERROR] El ejecutable no se generó correctamente")
            return None
            
    except ImportError:
        print("[ERROR] PyInstaller no está instalado. Ejecuta: pip install pyinstaller")
        return None
    except Exception as e:
        print(f"[ERROR] Fallo en la compilación: {e}")
        return None

def build_updater():
    """Build the updater executable using PyInstaller."""
    print("\n" + "="*50)
    print("[BUILD] Compilando ITMQ-Updater.exe...")
    print("="*50)
    
    script_path = get_abs_path('itmq_updater.py')
    manifest_path = get_abs_path("uac_manifest.xml")
    
    # PyInstaller arguments for updater (minimal dependencies)
    args_updater = [
        script_path,
        '--name=ITMQ-Updater',
        '--onefile',
        '--windowed',
        '--clean',
        '--noconfirm',
        '--distpath=dist',
        '--workpath=build',
        '--hidden-import=tkinter',
        '--hidden-import=urllib.request',
        f'--manifest={manifest_path}' if os.path.exists(manifest_path) else ''
    ]
    # Remove empty strings from args
    args_updater = [a for a in args_updater if a]
    
    try:
        import PyInstaller.__main__
        PyInstaller.__main__.run(args_updater)
        
        exe_path = get_abs_path(os.path.join('dist', 'ITMQ-Updater.exe'))
        
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"[OK] ITMQ-Updater.exe generado ({size_mb:.2f} MB)")
            return exe_path
        else:
            print("[ERROR] El updater no se generó correctamente")
            return None
            
    except ImportError:
        print("[ERROR] PyInstaller no está instalado. Ejecuta: pip install pyinstaller")
        return None
    except Exception as e:
        print(f"[ERROR] Fallo en la compilación del updater: {e}")
        return None

def main():
    """Main build process."""
    print("\n" + "="*50)
    print("  BUILD SCRIPT - ClasificadorPDF")
    print("="*50)
    
    # Load configuration
    config = load_config()
    print(f"\n[INFO] Versión: {config['version']}")
    print(f"[INFO] Repositorio: {config['github_repo']}")
    
    # Update version file
    version_data = update_version_file(config)
    
    # Build main application
    exe_path = build_executable(config)
    if not exe_path:
        print("\n[FATAL] No se pudo compilar la aplicación principal")
        sys.exit(1)
    
    # Build updater
    updater_path = build_updater()
    if not updater_path:
        print("\n[WARNING] El updater no se compiló, pero la app principal está lista")
    
    # Calculate and update SHA256
    print("\n" + "="*50)
    print("[INFO] Calculando SHA256...")
    print("="*50)
    
    sha256 = calculate_sha256(exe_path)
    if sha256:
        version_data['sha256'] = sha256
        with open(get_abs_path('version.json'), 'w', encoding='utf-8') as f:
            json.dump(version_data, f, indent=2, ensure_ascii=False)
        print(f"[OK] SHA256: {sha256}")
    else:
        print("[ERROR] No se pudo calcular el SHA256")
        sys.exit(1)
    
    # Final summary
    print("\n" + "="*50)
    print("  BUILD COMPLETADO")
    print("="*50)
    print(f"\nVersion: v{config['version']}")
    print(f"Aplicacion: {exe_path}")
    if updater_path:
        print(f"Updater: {updater_path}")
    print(f"SHA256: {sha256}")
    print(f"Fecha: {version_data['release_date']}")
    print("\nLos ejecutables estan listos en la carpeta 'dist/'")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()

