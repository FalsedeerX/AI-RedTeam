import os
from dotenv import load_dotenv

load_dotenv()

class RAGConfig:
    # Use an absolute path or relative to the service execution
    # Defaulting to a folder named 'chroma_db' inside the service directory

    # Paths relative to this package so they work regardless of CWD
    _CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))

    CHROMA_PERSIST_DIRECTORY = os.getenv(
        "CHROMA_PERSIST_DIRECTORY",
        os.path.join(_CONFIG_DIR, "chroma_db"),
    )

    # Model configuration
    # Updated based on demo_graph.py
    EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "bge-m3")
    LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "qwen3:8b")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434")
    
    # RAG parameters
    DOCS_SOURCE_DIRECTORY = os.getenv(
        "DOCS_SOURCE_DIRECTORY",
        os.path.join(_CONFIG_DIR, "lib"),
    )
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "example_collection")
    RETRIEVER_K = int(os.getenv("RETRIEVER_K", "5"))

    # Metasploit RPC Configuration
    # Ensure you start msfrpcd with: msfrpcd -P password -S false -U msf -a 127.0.0.1
    MSF_RPC_HOST = os.getenv("MSF_RPC_HOST", "172.31.191.206")
    MSF_RPC_PORT = int(os.getenv("MSF_RPC_PORT", "55552"))
    MSF_RPC_USER = os.getenv("MSF_RPC_USER", "msf")
    MSF_RPC_PASS = os.getenv("MSF_RPC_PASS", "msf123")
    MSF_RPC_SSL = os.getenv("MSF_RPC_SSL", "False").lower() == "true"

    LLM_SYSTEM_PROMPT = """You are a Security Research & Execution Assistant. 
You convert user intent into technical actions using provided documentation and execution tools.

Available Tools:
- `retrieve_context` — Search documentation / guides.
- `execute_nmap_scan` — Run an Nmap scan.
- `execute_msf_module` — Run a Metasploit auxiliary scanner or exploit module via MSF RPC.

Workflow:
1. **Reconnaissance**: Call `retrieve_context` to find technical specifications.
2. **Scanning**: Call `execute_nmap_scan` with the verified command.
3. **Verification / Exploitation** (when applicable): Analyse the Nmap output.
   - If open services or potential vulnerabilities are found, call `execute_msf_module` to verify them.
   - For example, if Nmap shows port 80 is open, you can run `execute_msf_module` with
     module_type='auxiliary', module_name='scanner/http/http_version',
     options={'RHOSTS': '<target>', 'RPORT': 80}.
   - For exploit modules you can similarly call `execute_msf_module` with module_type='exploit'.
4. **Output Analysis**: After running a Metasploit module, carefully read the console output to
   determine whether the vulnerability is confirmed, e.g., look for version banners, session
   creation, or "[+]" success indicators.

Rules:
1. Fact Supremacy: Documentation context > Internal memory. If the guide says a flag is incompatible, you MUST follow it.
2. The logic for the command must strictly adhere to the documentation provided.
3. Constraint Transparency: Before generating any command, explicitly list which flags/scan types are DISALLOWED for the requested technique.

Final Response Output Format:
- **Explanation**: [Summary from manual]
- **Command(s) Executed**: [Nmap command and/or MSF module used]
- **Execution Result**: [Output]
- **Vulnerability Assessment**: [Confirmed / Not confirmed / Needs further investigation]"""

    CRITIC_SYSTEM_PROMPT = """You are a Senior Security Auditor. 
Your task is to cross-check a proposed Nmap command against the provided documentation context.

Rules:
- If the command is 100% compliant with the documentation, reply ONLY with the string 'VALID', otherwise, explain the specific violation based on the manual and provide instructions for the fix.
"""

    def __init__(self):
        # Disable LangSmith unless user opts in (avoids 401 noise when not configured)
        if os.environ.get("LANGSMITH_TRACING") is None:
            os.environ["LANGSMITH_TRACING"] = "false"

config = RAGConfig()
