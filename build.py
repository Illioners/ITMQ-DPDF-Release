"""
Build Script for ClasificadorPDF (PyInstaller Version)
Updated for Dual-Repo Distribution (Private Source -> Public Release)
"""
import json
import os
import subprocess
import hashlib
import sys
from datetime import datetime

def get_abs_path(relative_path):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

def load_config():
    config_path = get_abs_path('build_config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def update_version_file(config):
    version = config['version']
    repo = config['github_repo']
    
    version_data = {
        "version": version,
        "release_date": datetime.now().strftime("%Y-%m-%d"),
        "download_url": f"https://github.com/{repo}/releases/download/v{version}/ClasificadorPDF.exe",
        "sha256": "",
        "changelog": "- Versión estable v1.1.1\n- Mejoras de rendimiento y limpieza de código\n- Categoría DOC añadida",
        "min_version": "1.0.0"
    }
    
    version_path = get_abs_path('version.json')
    with open(version_path, 'w', encoding='utf-8') as f:
        json.dump(version_data, f, indent=2, ensure_ascii=False)
    return version_data

def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def build_executable(config):
    print("\n[BUILD] Compilando aplicación con Nuitka...")
    script_path = get_abs_path('proglite.py')
    
    # Nuitka command for standalone onefile build
    command = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--windows-disable-console",
        "--enable-plugin=tk-inter",
        "--no-color",
        "--assume-yes-for-downloads",
        "--include-package=fitz",
        "--include-package=PIL",
        "--include-package=pytesseract",
        "--collect-all=fitz",
        "--collect-all=PIL",
        f"--include-data-file={get_abs_path('Intramaq-logo-mail.png')}=.",
        f"--include-data-file={get_abs_path('version.json')}=.",
        f"--include-data-file={get_abs_path('build_config.json')}=.",
        "--output-dir=dist",
        "--output-filename=ClasificadorPDF.exe",
        "--remove-output",
        "--no-pyi-file",
        script_path
    ]
    
    print(f"Ejecutando: {' '.join(command)}")
    result = subprocess.run(command)
    
    if result.returncode != 0:
        print("[ERROR] Fallo en la compilación con Nuitka")
        return None
    
    exe_path = get_abs_path(os.path.join('dist', 'ClasificadorPDF.exe'))
    return exe_path

def main():
    config = load_config()
    print(f"Preparando build v{config['version']}")
    
    version_data = update_version_file(config)
    exe_path = build_executable(config)
    
    if exe_path and os.path.exists(exe_path):
        sha256 = calculate_sha256(exe_path)
        version_data['sha256'] = sha256
        with open(get_abs_path('version.json'), 'w', encoding='utf-8') as f:
            json.dump(version_data, f, indent=2, ensure_ascii=False)
        
        print("\n" + "="*40)
        print(f"BUILD COMPLETADO: v{config['version']}")
        print(f"SHA256: {sha256}")
        print(f"Archivo: {exe_path}")
        print("="*40)
    else:
        print("[ERROR] No se encontró el ejecutable generado.")

if __name__ == "__main__":
    main()
