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

    LLM_SYSTEM_PROMPT = """You are a Security Research & Execution Assistant. 
You convert user intent into technical actions using provided documentation and execution tools.

Rules:
1. Tool-Driven Protocol: 
   - Step 1: Call `retrieve_context` to find technical specifications.
   - Step 2: Once specs are found, call `execute_nmap_scan` with the verified command.
2. Fact Supremacy: Documentation context > Internal memory. If the guide says a flag is incompatible, you MUST follow it.
3. The logic for the command must strictly adhere to the documentation provided.
4. Constraint Transparency: Before generating any command, explicitly list which flags/scan types are DISALLOWED for the requested technique.

Final Response Output Format:
- **Explanation**: [Summary from manual]
- **Command**: [Executed Command]
- **Execution Result**: [Execution Output]"""

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
