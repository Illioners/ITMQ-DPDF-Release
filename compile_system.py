import os
import shutil
import subprocess
import sys
import time

def print_step(msg):
    print("\n" + "="*50)
    print(f" {msg}")
    print("="*50)

def run_command(cmd, shell=True):
    print(f"> Executing: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    try:
        subprocess.check_call(cmd, shell=shell)
    except subprocess.CalledProcessError as e:
        print(f"!!! Error executing command: {e}")
        sys.exit(1)

def clean_dirs():
    print_step("1. CLEANING PREVIOUS BUILDS")
    for d in ["build", "dist"]:
        if os.path.exists(d):
            print(f"Removing {d}...")
            try:
                shutil.rmtree(d)
            except Exception as e:
                print(f"Warning: Could not remove {d}: {e}")

def check_dependencies():
    print_step("2. CHECKING DEPENDENCIES")
    if os.path.exists("requirements.txt"):
        run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    else:
        print("No requirements.txt found, skipping pip install.")

    # Check for PyInstaller
    try:
        subprocess.check_call(["pyinstaller", "--version"], shell=True, stdout=subprocess.DEVNULL)
    except:
        print("PyInstaller not found! Installing...")
        run_command([sys.executable, "-m", "pip", "install", "pyinstaller"])

def build_updater():
    print_step("3. COMPILING UPDATER (ITMQ-Updater)")
    spec_file = os.path.join("build_config", "ITMQ-Updater.spec")
    if not os.path.exists(spec_file):
        print(f"Error: Spec file {spec_file} not found!")
        sys.exit(1)
        
    cmd = ["pyinstaller", spec_file, "--clean", "--noconfirm", "--log-level=WARN"]
    run_command(cmd)
    
    # Verify
    if not os.path.exists(os.path.join("dist", "ITMQ-Updater", "ITMQ-Updater.exe")):
        print("Error: ITMQ-Updater.exe was not created!")
        sys.exit(1)

def build_proglite():
    print_step("4. COMPILING CLASIFICADOR PDF")
    spec_file = os.path.join("build_config", "proglite.spec")
    if not os.path.exists(spec_file):
        print(f"Error: Spec file {spec_file} not found!")
        sys.exit(1)
        
    cmd = ["pyinstaller", spec_file, "--clean", "--noconfirm", "--log-level=WARN"]
    run_command(cmd)
    
    # Verify
    if not os.path.exists(os.path.join("dist", "ClasificadorPDF", "ClasificadorPDF.exe")):
        print("Error: ClasificadorPDF.exe was not created!")
        sys.exit(1)

def build_app():
    print_step("5. COMPILING MAIN APP (PyQt/ITMQ-GD)")
    spec_file = os.path.join("build_config", "suite.spec")
    if not os.path.exists(spec_file):
        print(f"Error: Spec file {spec_file} not found!")
        sys.exit(1)

    cmd = ["pyinstaller", spec_file, "--clean", "--noconfirm", "--log-level=WARN"]
    run_command(cmd)

    # Cleanup AI Trainer if present (as requested previously)
    ai_trainer = os.path.join("dist", "ITMQ-GD-Suite", "EntrenadorAI.exe")
    if os.path.exists(ai_trainer):
        print("Removing EntrenadorAI.exe (Cleaning up)...")
        os.remove(ai_trainer)

def package_release():
    print_step("6. PACKAGING RELEASE (ZIPs)")
    dist_dir = os.path.abspath("dist")
    
    # --- Updater ZIP ---
    updater_dir = os.path.join(dist_dir, "ITMQ-Updater")
    if os.path.exists(updater_dir):
        zip_name = os.path.join(dist_dir, "ITMQ-Updater")
        print(f"Creating ITMQ-Updater.zip...")
        shutil.make_archive(zip_name, 'zip', root_dir=updater_dir)
    else:
        print("Error: ITMQ-Updater directory missing in dist!")

    # --- ClasificadorPDF ZIP ---
    lite_dir = os.path.join(dist_dir, "ClasificadorPDF")
    if os.path.exists(lite_dir):
        # Add Installer Script for Lite - DISABLED
        # iss_lite_src = os.path.join("build_config", "installer_lite.iss")
        # if os.path.exists(iss_lite_src):
        #     shutil.copy(iss_lite_src, lite_dir)
        #     print("Included installer_lite.iss")
        
        zip_name = os.path.join(dist_dir, "ClasificadorPDF")
        print(f"Creating ClasificadorPDF.zip...")
        shutil.make_archive(zip_name, 'zip', root_dir=dist_dir, base_dir="ClasificadorPDF")
    else:
        print("Warning: ClasificadorPDF directory missing in dist!")

    # --- Main Suite ZIP ---
    suite_dir = os.path.join(dist_dir, "ITMQ-GD-Suite")
    if os.path.exists(suite_dir):
        # Add Installer Script
        iss_src = os.path.join("build_config", "installer.iss")
        if os.path.exists(iss_src):
            shutil.copy(iss_src, suite_dir)
            print("Included installer.iss")
        
        # Add a README or instruction if needed
        # (Optional)
        
        zip_name = os.path.join(dist_dir, "ITMQ-GD")
        print(f"Creating ITMQ-GD.zip...")
        shutil.make_archive(zip_name, 'zip', root_dir=dist_dir, base_dir="ITMQ-GD-Suite")
    else:
        print("Error: ITMQ-GD-Suite directory missing in dist!")

    print_step("COMPILATION & PACKAGING COMPLETE")
    print(f"Outputs in: {dist_dir}")
    print(f"1. ITMQ-GD.zip (PyQt6 App + Installer Script)")
    print(f"2. ClasificadorPDF.zip (Tkinter App)")
    print(f"3. ITMQ-Updater.zip (Standalone Updater)")

if __name__ == "__main__":
    start_time = time.time()
    
    # Check for --fast flag to skip ITMQ-GD-Suite compilation
    fast_mode = "--fast" in sys.argv or "--quick" in sys.argv
    
    if fast_mode:
        print("\n" + "="*50)
        print(" FAST MODE: Skipping ITMQ-GD-Suite compilation")
        print("="*50 + "\n")
    
    clean_dirs()
    check_dependencies()
    build_updater()
    build_proglite()
    
    if not fast_mode:
        build_app()
    
    package_release()
    
    duration = time.time() - start_time
    print(f"\nDone in {duration:.2f} seconds.")
    
    if fast_mode:
        print("\nNote: ITMQ-GD-Suite was not compiled (fast mode).")
