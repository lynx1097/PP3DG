import sys
import platform
import subprocess
import json
import traceback
import psutil
from datetime import datetime
from pathlib import Path
from cryptography.fernet import Fernet
# Try importing New Relic SDK, fail gracefully if missing
try:
    from newrelic_telemetry_sdk import Log, LogClient
    NR_SDK_AVAILABLE = True
except ImportError:
    NR_SDK_AVAILABLE = False


# --- CONFIGURATION ---
base = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).parent.parent
key = (base / "_key.bin").read_bytes()
encrypted = (base / "_secrets.bin").read_bytes()

secrets = json.loads(Fernet(key).decrypt(encrypted))
NR_INSERT_KEY = secrets["NEW_RELIC_INSERT_KEY"]
# Use EU host if needed, otherwise default US
LOG_CLIENT = None
if NR_SDK_AVAILABLE and NR_INSERT_KEY:
    try:
        LOG_CLIENT = LogClient(NR_INSERT_KEY , host="log-api.eu.newrelic.com")
    except Exception as e:
        print(f"[Diag] Failed to init New Relic Client: {e}")

def get_gpu_info():
    """
    Cross-platform GPU detection.
    Returns a list of dicts containing Model, Driver, Type, etc.
    """
    system = platform.system()
    gpus = []

    try:
        if system == "Windows":
            # Use PowerShell to get detailed info as JSON
            cmd = "powershell \"Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,AdapterRAM,VideoProcessor,AdapterDACType | ConvertTo-Json\""
            output = subprocess.check_output(cmd, shell=True).decode()
            data = json.loads(output)
            if isinstance(data, dict): data = [data] # Handle single GPU case
            
            for item in data:
                ram_bytes = item.get("AdapterRAM", 0)
                # Logic: If RAM > 512MB and not Intel, likely Dedicated.
                is_dedicated = "Dedicated"
                if "Intel" in item.get("Name", "") or (ram_bytes and ram_bytes < 512*1024*1024):
                    is_dedicated = "Integrated"
                
                gpus.append({
                    "model": item.get("Name"),
                    "driver": item.get("DriverVersion"),
                    "type": is_dedicated,
                    "vram_mb": round(ram_bytes / (1024**2), 2) if ram_bytes else "Unknown"
                })

        elif system == "Darwin": # macOS
            # Use system_profiler
            cmd = ["system_profiler", "SPDisplaysDataType", "-json"]
            output = subprocess.check_output(cmd).decode()
            data = json.loads(output)
            items = data.get('SPDisplaysDataType', [])
            
            for item in items:
                # Apple Silicon often labeled as "Integrated" or "Unified"
                model = item.get("sppci_model", "Unknown")
                is_dedicated = "Integrated"
                if "Radeon" in model or "NVIDIA" in model:
                    is_dedicated = "Dedicated"
                
                gpus.append({
                    "model": model,
                    "driver": "Apple Metal/OS Default",
                    "type": is_dedicated,
                    "vram": item.get("spdisplays_vram", "Shared")
                })

        elif system == "Linux":
            # Use lspci
            cmd = "lspci -vnn | grep -A 12 'VGA compatible controller'"
            try:
                output = subprocess.check_output(cmd, shell=True).decode()
                current_gpu = {}
                for line in output.split('\n'):
                    if "VGA compatible controller" in line:
                        if current_gpu: gpus.append(current_gpu)
                        current_gpu = {"model": line.split(': ')[-1].strip(), "type": "Unknown"}
                        if "NVIDIA" in line or "AMD" in line: current_gpu["type"] = "Dedicated"
                        if "Intel" in line: current_gpu["type"] = "Integrated"
                    if "Kernel driver in use" in line and current_gpu:
                        current_gpu["driver"] = line.split(': ')[-1].strip()
                if current_gpu: gpus.append(current_gpu)
            except:
                pass # lspci might fail or not be installed

    except Exception as e:
        gpus.append({"error": f"Detection failed: {str(e)}"})

    return gpus

def get_system_specs():
    """Gather all system info for diagnostics."""
    try:
        mem = psutil.virtual_memory()
        uname = platform.uname()
        
        return {
            "os": uname.system,
            "os_release": uname.release,
            "machine": uname.machine,
            "python_version": sys.version.split()[0],
            "ram_total_gb": round(mem.total / (1024**3), 2),
            "ram_available_gb": round(mem.available / (1024**3), 2),
            "gpus": get_gpu_info(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

def send_crash_report(error_message, context="App Crash"):
    """Sends log to New Relic."""
    print(f"\n--- [DIAGNOSTIC] Sending Report: {context} ---")
    
    if not LOG_CLIENT:
        print(f"Skipping upload (No Key or SDK). Error was:\n{error_message}")
        return

    specs = get_system_specs()
    
    # Prepare attributes separately
    attributes = {
        "level": "ERROR",
        "service.name": "PP3DG",
        "context": context,
        "traceback": traceback.format_exc(),
        "app.os": specs.get("os"),
        "app.gpu_primary": specs.get("gpus", [{}])[0].get("model", "Unknown") if specs.get("gpus") else "None",
        "app.ram_gb": specs.get("ram_total_gb")
    }
    
    if specs.get("gpus"):
        attributes["app.gpu_details"] = json.dumps(specs["gpus"])

    try:
        # FIX: Pass 'message' as the first positional argument
        log = Log(message=error_message, attributes=attributes)
        LOG_CLIENT.send(log)
        print("Report sent to New Relic successfully.")
    except Exception as e:
        print(f"Failed to upload report: {e}")

# --- GLOBAL EXCEPTION HOOK ---
def handle_exception(exc_type, exc_value, exc_traceback):
    """
    Catches any uncaught exception in the application.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print("!!! CRITICAL ERROR CAUGHT !!!")
    print(error_msg)
    
    send_crash_report(f"{exc_type.__name__}: {exc_value}", context="Unhandled Crash")
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

def register_crash_handler():
    """Call this at app startup to catch crashes."""
    sys.excepthook = handle_exception
    print("[Diag] Crash Handler Registered")

if __name__ == "__main__":
    # Test Run
    print(json.dumps(get_system_specs(), indent=2))
    send_crash_report("Test Crash Report from DiagnosticModule", context="Test")