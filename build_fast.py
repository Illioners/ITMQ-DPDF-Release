"""
Quick Build Script - Compiles only ClasificadorPDF and ITMQ-Updater
Skips ITMQ-GD-Suite to save time (~6 minutes faster)
"""
import subprocess
import sys

if __name__ == "__main__":
    print("Starting FAST compilation (ClasificadorPDF + Updater only)...")
    print("This will skip ITMQ-GD-Suite compilation to save time.\n")
    
    # Run compile_system.py with --fast flag
    result = subprocess.run([sys.executable, "compile_system.py", "--fast"])
    
    sys.exit(result.returncode)
