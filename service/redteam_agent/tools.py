import re
import subprocess
import time
from langchain.tools import tool
from pymetasploit3.msfrpc import MsfRpcClient
from .config import config
from .run_state import check_killed, AgentCancelledError
from .vector_store import get_vector_store

# MSF global / payload settings that are valid msfconsole commands but are
# NOT listed in module.options (they belong to the payload or the console
# itself).  We must bypass the module.options check for these keys.
_MSF_GLOBAL_OPTIONS = frozenset({
    "LHOST", "LPORT", "PAYLOAD", "ENCODER", "NOPS", "TARGET",
    "SESSION", "THREADS",
})


def _strip_msf_banner(text: str) -> str:
    """Remove the Metasploit ASCII-art banner and boilerplate from console output.

    The banner ends with 'Rapid7 Open Source Project' followed by a blank line.
    Everything before (and including) that marker is stripped to save tokens.
    """
    # Match up to the last 'Rapid7 Open Source Project' line + trailing blank lines
    cleaned = re.sub(
        r"(?s)^.*Rapid7 Open Source Project\s*\n*",
        "",
        text,
    )
    return cleaned.strip() if cleaned.strip() else text.strip()


def _strip_nmap_noise(text: str) -> str:
    """Remove nmap service-fingerprint hex dumps and submission notices.

    These ``SF-Port`` blocks and ``NEXT SERVICE FINGERPRINT`` banners can
    easily be 1-2 KB of hex that provides zero decision value to the LLM.
    """
    # Remove "If you know the service/version...submit" lines
    text = re.sub(
        r"\d+ services? unrecognized despite returning data\..*?nmap\.org/cgi-bin/submit\.cgi\S*\s*:?",
        "",
        text,
        flags=re.DOTALL,
    )
    # Remove ==============NEXT SERVICE FINGERPRINT...============== blocks
    # Each block starts with the separator and ends before the next separator,
    # a known nmap output line (e.g. "Service Info:"), or end-of-string.
    text = re.sub(
        r"=+NEXT SERVICE FINGERPRINT.*?(?==+NEXT SERVICE|Service Info:|Nmap done:|$)",
        "",
        text,
        flags=re.DOTALL,
    )
    # Remove any leftover SF-Port lines
    text = re.sub(r"SF-Port.*\n?", "", text)
    # Collapse excessive blank lines left behind
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Maximum characters kept in a single tool output before truncation.
_MAX_OUTPUT_CHARS = 3000


def _truncate_output(text: str, limit: int = _MAX_OUTPUT_CHARS) -> str:
    """Truncate *text* to *limit* characters, appending a notice if clipped."""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[OUTPUT TRUNCATED — {len(text)} chars total, showing first {limit}]"

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

    _NMAP_TIMEOUT = 300
    _POLL_INTERVAL = 1

    try:
        check_killed()

        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        elapsed = 0
        while proc.poll() is None:
            time.sleep(_POLL_INTERVAL)
            elapsed += _POLL_INTERVAL

            try:
                check_killed()
            except AgentCancelledError:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                raise

            if elapsed >= _NMAP_TIMEOUT:
                proc.kill()
                proc.wait()
                return "Error: Nmap scan timed out (limit: 300s)."

        stdout, stderr = proc.communicate()
        full_output = stdout + "\n" + stderr
        full_output = _strip_nmap_noise(full_output)
        full_output = _truncate_output(full_output)

        if proc.returncode != 0:
            return f"Nmap execution failed (Exit Code {proc.returncode}):\n{full_output}"
        return f"Scan Execution Successful:\n{full_output}"

    except AgentCancelledError:
        raise
    except Exception as e:
        return f"System Error executing nmap: {str(e)}"

@tool
def search_msf_modules(keyword: str) -> str:
    """Search Metasploit's module database for modules matching a keyword.

    Call this BEFORE execute_msf_module to verify a module path actually exists
    in the running Metasploit instance and to discover the correct full path.

    Args:
        keyword: Search term (e.g., 'ms17_010', 'smb', 'eternalblue', 'ssl').
    """
    try:
        ssl_setting = config.MSF_RPC_SSL
        if isinstance(ssl_setting, str):
            ssl_setting = ssl_setting.lower() == "true"

        client = MsfRpcClient(
            password=config.MSF_RPC_PASS,
            username=config.MSF_RPC_USER,
            server=config.MSF_RPC_HOST,
            port=config.MSF_RPC_PORT,
            ssl=ssl_setting,
        )

        results = client.modules.search(keyword)
        if not results:
            return f"No modules found matching '{keyword}'."

        lines: list[str] = []
        for r in results[:30]:   # cap at 30 to avoid context bloat
            if isinstance(r, dict):
                fullname = r.get("fullname") or f"{r.get('type','?')}/{r.get('name','?')}"
                rank     = r.get("rank", "")
                desc     = (r.get("description") or "")[:70]
                lines.append(f"  {fullname}  [{rank}]  {desc}")
            else:
                lines.append(f"  {r}")

        header = f"Modules matching '{keyword}' ({len(results)} total, showing {len(lines)}):\n"
        return header + "\n".join(lines)

    except Exception as e:
        return f"Error searching MSF modules: {str(e)}"


@tool
def execute_msf_module(module_type: str, module_name: str, options: dict, payload: str = ""):
    """Execute a Metasploit module (auxiliary or exploit) via MSF RPC and return its console output.

    Use this tool to follow up on Nmap findings — for example, to verify a
    vulnerability with an auxiliary scanner or attempt a basic exploit.

    Args:
        module_type: Type of module (e.g., 'auxiliary', 'exploit').
        module_name: Full module path (e.g., 'scanner/http/http_version').
        options: Dictionary of module options (e.g., {'RHOSTS': '10.0.0.1', 'RPORT': 80}).
        payload: Metasploit payload to use (e.g., 'windows/meterpreter/reverse_tcp').
                 Only required for exploit modules. Leave empty for auxiliary modules.
    """
    try:
        check_killed()

        if module_name.startswith(f"{module_type}/"):
            module_name = module_name[len(module_type) + 1:]

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
        try:
            module = client.modules.use(module_type, module_name)
        except Exception as mod_err:
            return (
                f"Error: Module '{module_type}/{module_name}' not found or failed to load. "
                f"Detail: {mod_err}\n"
                f"Hint: Verify the module path is correct (e.g., 'scanner/smb/smb_version', "
                f"'windows/smb/ms17_010_eternalblue'). Use 'search' in msfconsole to find valid modules."
            )
        if not module:
            return f"Error: Module '{module_type}/{module_name}' not found."

        # --- 3. Build the console command string ---
        console_cmd = f"use {module_type}/{module_name}\n"

        # The LLM sometimes puts PAYLOAD inside the options dict.
        # Extract it here so it gets treated as a top-level console setting.
        effective_payload = payload or ""
        filtered_options: dict = {}
        for k, v in options.items():
            if k.upper() == "PAYLOAD":
                if not effective_payload:   # don't override the explicit param
                    effective_payload = str(v)
            else:
                filtered_options[k] = v

        # --- 3a. WSL networking: translate 127.0.0.1 → Windows host IP ---
        # When MSF_WSL_MODE is enabled, Metasploit runs inside WSL/Kali where
        # '127.0.0.1' resolves to WSL's own loopback, NOT the Windows host.
        # Auto-translate so modules can actually reach Windows services.
        if config.MSF_WSL_MODE:
            windows_host_ip = config.MSF_WINDOWS_HOST_IP
            if windows_host_ip:
                for key in list(filtered_options.keys()):
                    if key.upper() in ("RHOSTS", "RHOST"):
                        val = str(filtered_options[key]).strip()
                        if val in ("127.0.0.1", "localhost"):
                            filtered_options[key] = windows_host_ip

        if effective_payload:
            console_cmd += f"set PAYLOAD {effective_payload}\n"

        # --- 3b. Validate payload compatibility before running ---
        if effective_payload:
            try:
                valid_payloads = list(module.payloads)
                if valid_payloads and effective_payload not in valid_payloads:
                    # Suggest the most useful alternatives (prefer meterpreter)
                    meterpreter = [p for p in valid_payloads if "meterpreter" in p]
                    shells = [p for p in valid_payloads if "shell" in p and "meterpreter" not in p]
                    suggestions = (meterpreter + shells)[:8] or valid_payloads[:8]
                    return (
                        f"Error: Payload '{effective_payload}' is NOT compatible with "
                        f"module '{module_type}/{module_name}'.\n"
                        f"Compatible payloads (top suggestions):\n"
                        + "\n".join(f"  {p}" for p in suggestions)
                        + f"\n(Total compatible: {len(valid_payloads)})"
                    )
            except Exception:
                pass  # payloads list unavailable — proceed and let MSF report

        # Auto-inject LHOST for exploit modules using reverse-connection payloads.
        # Bind payloads (bind_tcp, bind_named_pipe …) do NOT need LHOST — they
        # listen on the TARGET, not the attacker.  Injecting LHOST for bind
        # payloads causes "[!] Unknown datastore option: LHOST" warnings.
        is_bind_payload = effective_payload and "bind" in effective_payload.lower()
        options_upper_keys = {k.upper() for k in filtered_options}

        # Strip LHOST the LLM may have put in options for bind payloads —
        # bind payloads listen on the target; LHOST is meaningless and causes
        # "[!] Unknown datastore option" warnings.
        if is_bind_payload:
            filtered_options = {
                k: v for k, v in filtered_options.items()
                if k.upper() != "LHOST"
            }
            options_upper_keys.discard("LHOST")

        needs_lhost = (
            module_type == "exploit"
            and "LHOST" not in options_upper_keys
            and not is_bind_payload
        )
        if needs_lhost:
            lhost = getattr(config, "MSF_LHOST", config.MSF_RPC_HOST)
            console_cmd += f"set LHOST {lhost}\n"

        for key, value in filtered_options.items():
            if key.upper() in _MSF_GLOBAL_OPTIONS:
                # Global / payload options are valid console commands but are
                # not listed in module.options — pass them through directly.
                console_cmd += f"set {key} {value}\n"
                continue
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

            try:
                check_killed()
            except AgentCancelledError:
                try:
                    console.destroy()
                except Exception:
                    pass
                raise

            res = console.read()
            if res["data"]:
                output_parts.append(res["data"])
            if res["busy"] is False:
                break
        else:
            output_parts.append("\n[WARNING] Module execution timed out (120 s).")

        # --- 6. Destroy the console to free resources ---
        try:
            console.destroy()
        except Exception:
            pass  # best-effort cleanup

        full_output = "\n".join(output_parts).strip()

        # Strip the MSF ASCII-art banner to save LLM context tokens
        full_output = _strip_msf_banner(full_output)
        full_output = _truncate_output(full_output)

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

    except AgentCancelledError:
        raise
    except Exception as e:
        return (
            f"System Error executing Metasploit: {str(e)}\n"
            f"Ensure msfrpcd is running: "
            f"'msfrpcd -P {config.MSF_RPC_PASS} -S {str(ssl_setting).lower()} "
            f"-U {config.MSF_RPC_USER} -a 0.0.0.0'"
        )

