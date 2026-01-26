import os
import shutil
import subprocess

def build():
    print(">>> Starting compilation...")
    
    # 1. Cleaning previous build
    if os.path.exists("dist"):
        try:
            shutil.rmtree("dist")
            print("Deleted dist/")
        except: pass
        
    if os.path.exists("build"):
        try:
            shutil.rmtree("build")
            print("Deleted build/")
        except: pass

    # 2. Run PyInstaller for Main Suite
    print(f"Building Main Suite...")
    cmd_suite = [
        "pyinstaller",
        "build_config/suite.spec",
        "--clean",
        "--noconfirm",
        "--log-level=WARN"
    ]
    subprocess.check_call(cmd_suite, shell=True)

    # 3. Run PyInstaller for Updater
    print(f"Building Updater...")
    cmd_updater = [
        "pyinstaller",
        "build_config/ITMQ-Updater.spec", 
        "--clean",
        "--noconfirm", 
        "--log-level=WARN"
    ]
    subprocess.check_call(cmd_updater, shell=True)
    
    # 4. Run PyInstaller for Proglite
    print(f"Building ClasificadorPDF...")
    cmd_proglite = [
        "pyinstaller",
        "build_config/proglite.spec", 
        "--clean",
        "--noconfirm", 
        "--log-level=WARN"
    ]
    subprocess.check_call(cmd_proglite, shell=True)
    
    # 5. Cleanup AI Trainer (User Request)
    ai_trainer_path = os.path.join("dist", "ITMQ-GD-Suite", "EntrenadorAI.exe")
    if os.path.exists(ai_trainer_path):
        os.remove(ai_trainer_path)
        print("Removed EntrenadorAI.exe (excluded from release)")

    print("\n[OK] Build Complete!")
    print(f"ITMQ-GD Suite: {os.path.abspath('dist/ITMQ-GD-Suite')}")
    print(f"ClasificadorPDF: {os.path.abspath('dist/ClasificadorPDF')}")
    print(f"Updater: {os.path.abspath('dist/ITMQ-Updater')}")

if __name__ == "__main__":
    build()