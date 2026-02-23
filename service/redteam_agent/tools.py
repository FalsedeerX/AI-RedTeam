import subprocess
import time
from langchain.tools import tool
from pymetasploit3.msfrpc import MsfRpcClient
from .config import config
from .vector_store import get_vector_store

@tool(response_format="content_and_artifact")
def retrieve_context(query: str):
    """Search the documentation/guide for specific query.
    
    Args:
        query: Search string to look up in the documents
    """
    vector_store = get_vector_store()
    retrieved_docs = vector_store.similarity_search(query, k=5)
    
    serialized = "\n\n".join(
        (f"Source: {doc.metadata}\nContent: {doc.page_content}")
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs    

@tool
def execute_nmap_scan(command: str):
    """Execute an Nmap scan command and return the results.
    
    Args:
        command: The full Nmap command string to execute.
    """
    # Security/Sanity check
    if not command.strip().lower().startswith("nmap"):
            return "Error: Command must start with 'nmap'."

    try:
        # Run the command
        # shell=True allows passing the full string on Windows
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=300 # 5 minutes timeout
        )
        # Combine stdout and stderr
        full_output = result.stdout + "\n" + result.stderr
        
        if result.returncode != 0:
            return f"Nmap execution failed (Exit Code {result.returncode}):\n{full_output}"
        return f"Scan Execution Successful:\n{full_output}"
        
    except subprocess.TimeoutExpired:
        return "Error: Nmap scan timed out (limit: 300s)."
    except Exception as e:
        return f"System Error executing nmap: {str(e)}"

@tool
def execute_msf_module(module_type: str, module_name: str, options: dict):
    """Execute a Metasploit module (auxiliary or exploit) via MSF RPC and return its console output.

    Use this tool to follow up on Nmap findings — for example, to verify a
    vulnerability with an auxiliary scanner or attempt a basic exploit.

    Args:
        module_type: Type of module (e.g., 'auxiliary', 'exploit').
        module_name: Full module path (e.g., 'scanner/http/http_version').
        options: Dictionary of module options (e.g., {'RHOSTS': '10.0.0.1', 'RPORT': 80}).
    """
    try:
        # --- 1. Connect to MSF RPC ---
        ssl_setting = config.MSF_RPC_SSL
        if isinstance(ssl_setting, str):
            ssl_setting = ssl_setting.lower() == 'true'

        client = MsfRpcClient(
            password=config.MSF_RPC_PASS,
            username=config.MSF_RPC_USER,
            server=config.MSF_RPC_HOST,
            port=config.MSF_RPC_PORT,
            ssl=ssl_setting,
        )

        # --- 2. Validate module exists ---
        module = client.modules.use(module_type, module_name)
        if not module:
            return f"Error: Module '{module_type}/{module_name}' not found."

        # --- 3. Build the console command string ---
        console_cmd = f"use {module_type}/{module_name}\n"
        for key, value in options.items():
            if key not in module.options:
                return (
                    f"Error: Invalid option '{key}' for module '{module_name}'. "
                    f"Valid options: {list(module.options)}"
                )
            console_cmd += f"set {key} {value}\n"
        # 'run' works for both auxiliary and exploit modules in msfconsole
        console_cmd += "run\n"

        # --- 4. Create an interactive console and send the command ---
        console = client.consoles.console()
        console.write(console_cmd)

        # --- 5. Poll until the console is no longer busy ---
        output_parts: list[str] = []
        poll_interval = 2          # seconds between polls
        max_wait      = 120        # total seconds before timeout
        elapsed       = 0

        while elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval
            res = console.read()
            if res["data"]:
                output_parts.append(res["data"])
            if res["busy"] is False:
                break
        else:
            # Timed-out — still collect whatever we have
            output_parts.append("\n[WARNING] Module execution timed out (120 s).")

        # --- 6. Destroy the console to free resources ---
        try:
            console.destroy()
        except Exception:
            pass  # best-effort cleanup

        full_output = "".join(output_parts).strip()

        # --- 7. Check for new sessions (exploit follow-up) ---
        session_info = ""
        try:
            sessions = client.sessions.list
            if sessions:
                session_info = f"\n\n[+] Active sessions ({len(sessions)}):\n"
                for sid, sdata in sessions.items():
                    session_info += (
                        f"  Session {sid}: type={sdata.get('type')} "
                        f"target={sdata.get('session_host')}:{sdata.get('session_port')} "
                        f"info={sdata.get('info')}\n"
                    )
        except Exception:
            pass  # non-critical

        if not full_output:
            return (
                f"Module {module_type}/{module_name} executed but produced no console output."
                f"{session_info}"
            )

        return f"Metasploit Output:\n{full_output}{session_info}"

    except Exception as e:
        return (
            f"System Error executing Metasploit: {str(e)}\n"
            f"Ensure msfrpcd is running: "
            f"'msfrpcd -P {config.MSF_RPC_PASS} -S {str(ssl_setting).lower()} "
            f"-U {config.MSF_RPC_USER} -a 0.0.0.0'"
        )

