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
        "changelog": "- Eliminado error de Python al actualizar\n- Agregada notificación de éxito tras la instalación\n- Cierre de proceso optimizado",
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

def sign_executable(exe_path):
    pfx_path = get_abs_path("TC_CodeSigning.pfx")
    if os.path.exists(pfx_path) and os.path.exists(exe_path):
        print(f"\n[SIGN] Firmando {os.path.basename(exe_path)}...")
        
        ps_command = f'''
        try {{
            $pfxPath = "{pfx_path}"
            $exePath = "{exe_path}"
            $pass = ConvertTo-SecureString -String "ClasificadorPDF2026" -Force -AsPlainText
            $cert = Get-PfxCertificate -FilePath $pfxPath -Password $pass
            
            if ($cert) {{
                Set-AuthenticodeSignature -FilePath $exePath -Certificate $cert
                exit 0
            }} else {{
                Write-Error "No se pudo cargar el certificado."
                exit 1
            }}
        }} catch {{
            Write-Error $_.Exception.Message
            exit 1
        }}
        '''
        
        result = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-NonInteractive", "-Command", ps_command], capture_output=True, text=True)
        
        if result.returncode == 0 and "Valid" in result.stdout:
            print(f"[SIGN] ÉXITO: {os.path.basename(exe_path)} firmado correctamente.")
            return True
        else:
            print(f"[SIGN] ADVERTENCIA: La firma podría no haber sido perfecta.\nSalida: {result.stdout}")
    return False

def build_executable(config):
    print("\n[BUILD] Compilando aplicación PRINCIPAL con PyInstaller...")
    script_path = get_abs_path('proglite.py')
    
    # Argumentos para PyInstaller - APP PRINCIPAL
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
        f'--manifest={get_abs_path("uac_manifest.xml")}'
    ]
    
    try:
        import PyInstaller.__main__
        PyInstaller.__main__.run(args_main)
        exe_path = get_abs_path(os.path.join('dist', 'ClasificadorPDF.exe'))
        sign_executable(exe_path)
        return exe_path
    except Exception as e:
        print(f"[ERROR] Fallo en PyInstaller (Main): {e}")
        return None

def build_updater():
    print("\n[BUILD] Compilando ITMQ-Updater con PyInstaller...")
    script_path = get_abs_path('itmq_updater.py')
    
    # Argumentos para PyInstaller - UPDATER
    # Notar: El updater no necesita tantos recursos como la app principal
    args_updater = [
        script_path,
        '--name=ITMQ-Updater',
        '--onefile',
        '--windowed',
        '--clean',
        '--noconfirm',
        '--distpath=dist',
        '--workpath=build',
        # Minimal imports usually needed for tkinter + url access
        '--hidden-import=tkinter',
        '--hidden-import=urllib.request' 
    ]
    
    try:
        import PyInstaller.__main__
        PyInstaller.__main__.run(args_updater)
        exe_path = get_abs_path(os.path.join('dist', 'ITMQ-Updater.exe'))
        sign_executable(exe_path)
        return exe_path
    except Exception as e:
        print(f"[ERROR] Fallo en PyInstaller (Updater): {e}")
        return None

def main():
    config = load_config()
    print(f"Preparando build v{config['version']}")
    
    version_data = update_version_file(config)
    
    # Build Main App
    exe_path = build_executable(config)
    
    # Build Updater
    updater_path = build_updater()
    
    if exe_path and os.path.exists(exe_path):
        sha256 = calculate_sha256(exe_path)
        version_data['sha256'] = sha256
        with open(get_abs_path('version.json'), 'w', encoding='utf-8') as f:
            json.dump(version_data, f, indent=2, ensure_ascii=False)
        
        print("\n" + "="*40)
        print(f"BUILD COMPLETADO: v{config['version']}")
        print(f"SHA256 (App): {sha256}")
        print(f"Archivo App: {exe_path}")
        if updater_path and os.path.exists(updater_path):
             print(f"Archivo Updater: {updater_path}")
        else:
             print("ADVERTENCIA: ITMQ-Updater no se generó correctamente.")
        print("="*40)
    else:
        print("[ERROR] No se encontró el ejecutable generado.")
        sys.exit(1)

if __name__ == "__main__":
    main()
