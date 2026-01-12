"""
Build Script for ClasificadorPDF
Automates the build process with PyInstaller
"""
import json
import os
import subprocess
import hashlib
import sys
from datetime import datetime

# Set encoding for stdout to handle potential issues
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def get_abs_path(relative_path):
    """Get absolute path relative to script location"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

def load_config():
    """Load build configuration"""
    config_path = get_abs_path('build_config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] No se encontró {config_path}")
        sys.exit(1)

def update_version_file(config):
    """Update version.json with current build info"""
    version = config['version']
    repo = config['github_repo']
    
    version_data = {
        "version": version,
        "release_date": datetime.now().strftime("%Y-%m-%d"),
        "download_url": f"https://github.com/{repo}/releases/download/v{version}/ClasificadorPDF.exe",
        "sha256": "",  # Will be filled after build
        "changelog": "- Ver notas de la versión en GitHub",
        "min_version": "1.0.0"
    }
    
    version_path = get_abs_path('version.json')
    try:
        with open(version_path, 'w', encoding='utf-8') as f:
            json.dump(version_data, f, indent=2, ensure_ascii=False)
        print(f"[INFO] version.json actualizado para v{version}")
    except Exception as e:
        print(f"[ERROR] No se pudo escribir {version_path}: {e}")
        sys.exit(1)
        
    return version_data

def calculate_sha256(file_path):
    """Calculate SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"[ERROR] No se pudo calcular el hash de {file_path}: {e}")
        return ""

def build_executable(config):
    """Build the executable using PyInstaller"""
    print("\n[BUILD] Compilando aplicación...")
    
    # Run PyInstaller
    # Using the spec file which should be in the same directory
    spec_path = get_abs_path('ClasificadorPDF.spec')
    result = subprocess.run(
        ['pyinstaller', spec_path, '--clean'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("[ERROR] Error durante la compilación:")
        print(result.stderr)
        return None
    
    exe_path = get_abs_path(os.path.join('dist', 'ClasificadorPDF.exe'))
    
    if not os.path.exists(exe_path):
        print("[ERROR] El ejecutable no fue generado")
        return None
    
    print(f"[SUCCESS] Ejecutable compilado: {exe_path}")
    return exe_path

def update_sha256(exe_path, version_data):
    """Calculate and update SHA256 in version.json"""
    print("\n[HASH] Calculando SHA256...")
    
    sha256 = calculate_sha256(exe_path)
    if not sha256:
        return ""
        
    version_data['sha256'] = sha256
    
    version_path = get_abs_path('version.json')
    try:
        with open(version_path, 'w', encoding='utf-8') as f:
            json.dump(version_data, f, indent=2, ensure_ascii=False)
        print(f"[INFO] SHA256: {sha256}")
    except Exception as e:
        print(f"[ERROR] No se pudo actualizar {version_path}: {e}")
        
    return sha256

def generate_release_notes(config, sha256):
    """Generate release notes file"""
    version = config['version']
    
    notes = f"""# Release v{version}

## Información del Build

- **Versión**: {version}
- **Fecha**: {datetime.now().strftime("%Y-%m-%d %H:%M")}
- **SHA256**: `{sha256}`

## Instalación

1. Descarga `ClasificadorPDF.exe`
2. Verifica el hash SHA256 (opcional pero recomendado)
3. Ejecuta el instalador

## Notas

- Esta versión incluye actualizaciones automáticas
- El sistema verificará automáticamente nuevas versiones al iniciar

## Changelog

- Ver commits desde la última versión para detalles completos
"""
    
    notes_path = get_abs_path('RELEASE_NOTES.md')
    try:
        with open(notes_path, 'w', encoding='utf-8') as f:
            f.write(notes)
        print(f"[INFO] Notas de release generadas: RELEASE_NOTES.md")
    except Exception as e:
        print(f"[ERROR] No se pudo escribir {notes_path}: {e}")

def main():
    """Main build process"""
    print("=" * 60)
    print("  ClasificadorPDF - Build Script")
    print("=" * 60)
    
    # Load configuration
    config = load_config()
    print(f"\n[INIT] Preparando build para v{config['version']}")
    
    # Update version.json (empty SHA for now)
    version_data = update_version_file(config)
    
    # Build executable
    exe_path = build_executable(config)
    if not exe_path:
        sys.exit(1)
    
    # Calculate and update SHA256
    sha256 = update_sha256(exe_path, version_data)
    
    # Generate release notes
    generate_release_notes(config, sha256)
    
    # Get file size
    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    
    print("\n" + "=" * 60)
    print("[DONE] BUILD COMPLETADO")
    print("=" * 60)
    print(f"Versión: v{config['version']}")
    print(f"Ejecutable: {exe_path}")
    print(f"Tamaño: {size_mb:.2f} MB")
    print(f"SHA256: {sha256}")
    print("\n[NEXT] Próximos pasos:")
    print("1. Prueba el ejecutable localmente")
    print("2. Crea un tag: git tag v" + config['version'])
    print("3. Push del tag: git push origin v" + config['version'])
    print("4. GitHub Actions creará el release automáticamente")
    print("=" * 60)

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
