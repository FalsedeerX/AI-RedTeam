
import sys
import os
import time

# Add current directory to path so we can import 'redteam_agent' package
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")

from service.redteam_agent.tools import execute_msf_module
from service.redteam_agent.config import config

def test_msf_connection():
    print("=== Testing MSF RPC Connection ===")
    print(f"Connecting to {config.MSF_RPC_HOST}:{config.MSF_RPC_PORT} as user '{config.MSF_RPC_USER}'...")

    # We can try to use a harmless auxiliary module just to see if we can connect and set options.
    # 'auxiliary/scanner/portscan/tcp' is a good candidate.
    
    module_type = "auxiliary"
    module_name = "scanner/portscan/tcp"
    
    # Intentionally picking a safe target (localhost) and a single port to avoid noise
    target_options = {
        "RHOSTS": "127.0.0.1",
        "PORTS": "135" # Common windows port, or just pick random
    }
    
    print(f"Attempting to load module: {module_type}/{module_name}")
    print(f"Options: {target_options}")
    
    try:
        result = execute_msf_module.invoke({
            "module_type": module_type,
            "module_name": module_name,
            "options": target_options
        })
        
        print("\n[Tool Output]:")
        print(result)
        
        if "Error" in result:
            print("\n❌ Test Failed.")
        else:
            print("\n✅ Test Passed: Module executed via RPC.")
            
    except Exception as e:
        print(f"\n❌ Exception during test: {e}")

if __name__ == "__main__":
    test_msf_connection()
