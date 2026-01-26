import sys
import os

# Mock fitz so we can import proglite without installing dependencies or launching GUI
from unittest.mock import MagicMock
sys.modules['fitz'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['tkinter'] = MagicMock()
sys.modules['tkinter.filedialog'] = MagicMock()
sys.modules['tkinter.messagebox'] = MagicMock()

# Manually define the PROFILES structure if import fails, 
# but let's try to import specifically the PROFILES dict if possible.
# Actually, proglite.py has a lot of GUI code at module level? 
# Looking at the file, the GUI code is inside classes, but there might be some global inits.
# Let's read the file content and extract PROFILES dictionary using exec() to avoid module level side effects.

def load_profiles_from_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract the PROFILES dictionary part
    # We look for "PROFILES = {" and the matching closing brace
    import ast
    
    # simpler: just parse the whole file as ast and find assignment to PROFILES
    tree = ast.parse(content)
    profiles_dict = None
    
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'PROFILES':
                    # verify it's a dict
                    if isinstance(node.value, ast.Dict):
                        # We can interpret this literal safely
                        profiles_dict = ast.literal_eval(node.value)
    
    return profiles_dict

def test_profiles():
    try:
        profiles = load_profiles_from_file(r'c:\Users\tomas\Desktop\CLASSPDF\proglite.py')
    except Exception as e:
        # Fallback if AST parsing gets complex (e.g. comments or non-literals in dict)
        print(f"AST parsing failed: {e}")
        # Try a simpler direct evaluation of the dict string if we can isolate it,
        # but the AST approach is robust for literals.
        # Actually proglite PROFILES contains comments which ast.literal_eval handles if from ast node?
        # No, ast.literal_eval works on expression strings or nodes involved in literals.
        # The PROFILES definition in proglite.py seems to only use string literals and lists/dicts.
        # It should work.
        return

    print("Successfully loaded PROFILES")
    
    # 1. Verify Ingreso matches Gestion Humana
    gh = profiles.get("Gestion Humana")
    ing = profiles.get("Ingreso")
    
    if gh == ing:
        print("[PASS] 'Ingreso' profile matches 'Gestion Humana' exactly.")
    else:
        print("[FAIL] 'Ingreso' profile DOES NOT match 'Gestion Humana'.")
        # Diff details could be added here
        
    # 2. Verify En Curso
    ec = profiles.get("En Curso")
    if ec and "Novedades" in ec["SEGMENTS"]:
        print("[PASS] 'En Curso' profile has 'Novedades' segment.")
    else:
        print("[FAIL] 'En Curso' missing 'Novedades'.")

    # 3. Verify Retiro
    ret = profiles.get("Retiro")
    if ret and "Terminación" in ret["SEGMENTS"]:
        print("[PASS] 'Retiro' profile has 'Terminación' segment.")
    else:
        print("[FAIL] 'Retiro' missing 'Terminación'.")
        
    # 4. Test Merging Logic (Logic copied from MainApp.select_files)
    active_names = ["Ingreso", "Retiro"]
    print(f"\nTesting merging of: {active_names}")
    
    merged_cats = []
    merged_segs = {}
    processed_abbrs = set()
    
    for name in active_names:
        p_data = profiles[name]
        # Categories
        for abbr, cat_name in p_data["CATEGORIES"]:
            if abbr not in processed_abbrs:
                merged_cats.append((abbr, cat_name))
                processed_abbrs.add(abbr)
                
        # Segments
        for seg_name, abbrs in p_data["SEGMENTS"].items():
            merged_segs[seg_name] = abbrs

    # check results
    print(f"Merged Categories Count: {len(merged_cats)}")
    print(f"Merged Segments Keys: {list(merged_segs.keys())}")
    
    # Expected segments: A. Contrato... D. Documentos (from Ingreso) AND Terminación (from Retiro)
    expected_segments = ["A. Contrato", "B. Afiliaciones", "C. Certificaciones", "D. Documentos adicionales", "Terminación"]
    missing_segments = [s for s in expected_segments if s not in merged_segs]
    
    if not missing_segments:
        print("[PASS] Merging produced all expected segments.")
    else:
        print(f"[FAIL] Missing segments after merge: {missing_segments}")

if __name__ == "__main__":
    test_profiles()
