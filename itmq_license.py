import os
import hashlib
import uuid
import json
import base64
import datetime
import urllib.request
from datetime import datetime, timedelta

# Salt for security
SECRET_SALT = "ITMQ_GD_S3CR3T_2026"

# Duration types
DURATIONS = {
    "7D": 7,
    "30D": 30,
    "90D": 90,
    "365D": 365,
    "LIFETIME": 99999
}

def get_machine_id():
    """Generates a unique, stable Machine ID based on hardware."""
    try:
        node = uuid.getnode()
        raw_id = f"{node}-{SECRET_SALT}"
        return hashlib.sha256(raw_id.encode()).hexdigest()[:16].upper()
    except:
        return "UNKNOWN-HWID-0000"

def generate_key(duration_type="30D"):
    """
    Generates a universal Master Key for a given duration.
    No longer requires a machine_id.
    """
    # Use a fixed string for universal keys instead of HWID
    raw = f"MASTER:{SECRET_SALT}:{duration_type}"
    h = hashlib.sha256(raw.encode()).hexdigest().upper()
    # Format: XXXX-XXXX-XXXX-XXXX
    return f"{h[0:4]}-{h[8:12]}-{h[16:20]}-{h[24:28]}"

def calculate_signature(data_dict):
    """
    Calculates a digital signature for a dictionary to prevent tampering.
    Includes HWID to bind the LOCAL file to THIS machine.
    """
    hwid = get_machine_id()
    items = sorted([(k, v) for k, v in data_dict.items() if k != "signature"])
    raw_str = f"{items}:{hwid}:{SECRET_SALT}"
    return hashlib.sha256(raw_str.encode()).hexdigest()

def validate_key(key):
    """
    Validates if a key is a valid Master Key and returns the duration type.
    Returns None if invalid.
    """
    if not key or len(key) < 15:
        return None
    
    key = key.strip().upper()
    for dtype in DURATIONS.keys():
        if key == generate_key(dtype):
            return dtype
    return None

def get_license_file():
    appdata = os.getenv('LOCALAPPDATA', os.path.expanduser('~'))
    return os.path.join(appdata, "ITMQ-GD", "license.lic") 

def save_license(key, duration_type, custom_activation_date=None):
    path = get_license_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    # Use custom activation date if provided, otherwise use current time
    if custom_activation_date:
        activation_date = custom_activation_date
    else:
        activation_date = datetime.now()
    
    days = DURATIONS.get(duration_type, 30)
    expiry_date = activation_date + timedelta(days=days)
    
    data = {
        "key": key.strip().upper(),
        "type": duration_type,
        "activation_date": activation_date.isoformat(),
        "expiry_date": expiry_date.isoformat()
    }
    
    # Add signature for integrity (This binds the .lic file to the hardware)
    data["signature"] = calculate_signature(data)
    
    try:
        # Obfuscate with Base64
        json_str = json.dumps(data)
        obfuscated = base64.b64encode(json_str.encode()).decode()
        
        with open(path, "w") as f:
            f.write(obfuscated)
        return True
    except:
        return False

def load_license_data():
    path = get_license_file()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            content = f.read().strip()
            
        # De-obfuscate
        decoded = base64.b64decode(content).decode()
        data = json.loads(decoded)
        
        # Verify Signature (Integrity & HWID match)
        sig = data.get("signature")
        if not sig or sig != calculate_signature(data):
            # If signature doesn't match, it means it was tampered OR copied from another PC
            return None
            
        return data
    except Exception:
        return None

def is_activated():
    """Check if the current machine has a valid, non-expired, and non-tampered license."""
    data = load_license_data()
    if not data:
        return False
    
    # 1. Validate key still matches universal pattern
    current_key = data.get("key")
    current_type = data.get("type")
    if validate_key(current_key) != current_type:
        return False
        
    # 2. Check Expiration
    if current_type == "LIFETIME":
        return True
        
    try:
        expiry = datetime.fromisoformat(data.get("expiry_date"))
        if datetime.now() > expiry:
            return False
        return True
    except:
        return False

def get_remaining_days():
    """Returns days left in license or None if lifetime/error."""
    data = load_license_data()
    if not data:
        return 0
    if data.get("type") == "LIFETIME":
        return None
    try:
        expiry = datetime.fromisoformat(data.get("expiry_date"))
        delta = expiry - datetime.now()
        # Ensure we return at least 1 if it's the same day but not expired
        days = delta.days + (1 if delta.total_seconds() > 0 and delta.days == 0 else 0)
        return max(0, days)
    except:
        return 0

# Remote Activation Config
# The JSON should look like: {"authorized_ids": {"HWID_HERE": "LIFETIME", "ANOTHER_ID": "365D"}}
REMOTE_ACTIVATION_URL = "https://raw.githubusercontent.com/Illioners/ITMQ-DPDF/main/licenses.json"

def check_online_activation():
    """
    Checks a remote server to see if this Machine ID is pre-authorized.
    If authorized, activates the app locally.
    """
    if is_activated():
        # But maybe we should check if the online one is "better" (e.g. trial -> lifetime)
        data = load_license_data()
        if data and data.get("type") == "LIFETIME":
            return True # Already at max level
            
    hwid = get_machine_id()
    try:
        # Use a short timeout to not block startup too much
        with urllib.request.urlopen(REMOTE_ACTIVATION_URL, timeout=5) as response:
            if response.status == 200:
                remote_data = json.loads(response.read().decode())
                authorized = remote_data.get("authorized_ids", {})
                
                if hwid in authorized:
                    dtype = authorized[hwid]
                    # Generate a master key for the authorized duration
                    key = generate_key(dtype)
                    if save_license(key, dtype):
                        print(f"Automatic Online Activation Success: {dtype}")
                        return True
    except Exception as e:
        print(f"Online check failed or timed out: {e}")
        
    return False

def get_license_status_text():
    """Returns a short string for the window title."""
    if not is_activated():
        return "Licencia: NO ACTIVADA"
    
    data = load_license_data()
    if not data: return "Licencia: Inválida"
    
    ltype = data.get("type")
    if ltype == "LIFETIME":
        return "Licencia: Vitalicia"
    
    days = get_remaining_days()
    if ltype == "7D":
        return f"Prueba: {days} días restantes"
    return f"Licencia: {days} días restantes"

def ensure_trial_initiated():
    """Starts a 7-day trial if no license exists and trial hasn't been used."""
    if is_activated():
        return True
    
    # Check if trial was already used in user_settings
    # (We assume the app imports settings elsewhere, here we use a local check)
    path = get_license_file()
    if os.path.exists(path):
        return False # License file exists but is invalid/expired
        
    # Generate a trial key for THIS machine
    hwid = get_machine_id() 
    # Default trial is 7 days starting from January 28, 2026
    trial_key = generate_key("7D")
    # Set custom activation date to January 28, 2026
    trial_start_date = datetime(2026, 1, 28, 0, 0, 0)
    return save_license(trial_key, "7D", custom_activation_date=trial_start_date)

if __name__ == "__main__":
    # Internal Test / Key Gen Tool
    mid = get_machine_id()
    print(f"Machine ID: {mid}")
    print("--- LICENSE KEYS ---")
    mid = get_machine_id() 
    for d in DURATIONS:
        print(f"{d}: {generate_key(d)}")
