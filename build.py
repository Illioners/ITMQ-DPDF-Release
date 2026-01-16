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

    # 2. Run PyInstaller
    cmd = [
        "pyinstaller",
        "build_config/suite.spec",
        "--clean",
        "--noconfirm",
        "--log-level=WARN"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    subprocess.check_call(cmd, shell=True)
    
    print("\n[OK] Build Complete!")
    print(f"Output: {os.path.abspath('dist/ITMQ-GD-Suite')}")

if __name__ == "__main__":
    build()