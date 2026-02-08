import subprocess
from langchain.tools import tool
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
