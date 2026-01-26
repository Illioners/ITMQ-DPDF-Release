"""
Quick Build Script - Compiles ClasificadorPDF, ITMQ-Updater, and Setup
Skips ITMQ-GD-Suite to save time (~6 minutes faster)
"""
import subprocess
import sys
import os

if __name__ == "__main__":
    print("Starting FAST compilation (ClasificadorPDF + Updater + Setup)...")
    print("This will skip ITMQ-GD-Suite compilation to save time.\n")
    
    # Step 1: Run compile_system.py with --fast flag
    print("=" * 50)
    print("STEP 1: Compiling executables...")
    print("=" * 50)
    result = subprocess.run([sys.executable, "compile_system.py", "--fast"])
    
    if result.returncode != 0:
        print("\n[ERROR] Compilation failed!")
        sys.exit(result.returncode)
    
    # Step 2: Compile installer with Inno Setup
    print("\n" + "=" * 50)
    print("STEP 2: Compiling installer (Setup)...")
    print("=" * 50)
    
    inno_setup_path = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    installer_script = r"build_config\installer_lite.iss"
    
    if not os.path.exists(inno_setup_path):
        print(f"[WARNING] Inno Setup not found at {inno_setup_path}")
        print("Skipping installer compilation.")
        sys.exit(0)
    
    try:
        result = subprocess.run(
            [inno_setup_path, installer_script],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("[OK] Setup compiled successfully!")
            # Extract filename from output
            for line in result.stdout.split('\n'):
                if 'Resulting Setup program filename is:' in line:
                    print(f"[PACKAGE] {line.strip()}")
        else:
            print("[ERROR] Setup compilation failed!")
            print(result.stderr)
            sys.exit(result.returncode)
            
    except Exception as e:
        print(f"[ERROR] Error compiling setup: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("[SUCCESS] FAST BUILD COMPLETE!")
    print("=" * 50)
    print("\nGenerated files in dist/:")
    print("  - ClasificadorPDF.zip")
    print("  - ITMQ-Updater.zip")
    print("  - ClasificadorPDF_Setup_vX.X.X.exe")
    
    sys.exit(0)

