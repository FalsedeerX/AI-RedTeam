import os
from langchain.tools import tool
from langchain.agents import create_agent
from langchain.messages import AnyMessage, SystemMessage, ToolMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_chroma import Chroma
from typing import Literal
from typing_extensions import TypedDict, Annotated
import operator

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGSMITH_PROJECT"] = "My First App"
LLM_NAME = "qwen3:8b"
EMBED_NAME = "bge-m3"

LLM_SYSTEM_PROMPT = """### Role
Security Research & Execution Assistant. You convert user intent into technical actions using provided documentation and execution tools.

### Rules
1. **Tool-Driven Protocol**: 
   - Step 1: Call `retrieve_context` to find technical specifications.
   - Step 2: Once specs are found, call `execute_nmap_scan` with the verified command.
2. **Fact Supremacy**: Documentation context > Internal memory. If the guide says a flag is incompatible (e.g., `-f` vs `--mtu`), you MUST follow it.
3. **Logic Check**: 
   - Flags must support the scan type (e.g., fragmentation does NOT support `-sT`).
   - Numerical offsets (like MTU) must be multiples of 8.
4. **Constraint Transparency**: Before generating any command, explicitly list which flags/scan types are DISALLOWED for the requested technique.

### Output Format (For Final Response)
- **Constraint Analysis**: [List disallowed options found in context]
- **Flag**: [Flag Name]
- **Explanation**: [Summary from manual]
- **Command**: 
```bash
[Verified Command]"""

CRITIC_SYSTEM_PROMPT = """You are a Senior Security Auditor. 
Your task is to cross-check a proposed Nmap command against the provided documentation context.

Check specifically for:
1. **Flag Exclusivity**: e.g., Ensuring '-f' and '--mtu' are NOT used together.
2. **Scan Type Support**: e.g., Confirming that the scan type (like -sS) supports fragmentation, while others (like -sT) do not.
3. **Mathematical Constraints**: e.g., Verifying that the MTU value is a multiple of 8.

Rules:
- If the command is 100% compliant with the documentation, reply ONLY with the string 'VALID'.
- If there is a conflict or error, explain the specific violation based on the manual and provide instructions for the fix.
"""

# Step 1: Define tools and model

embeddings = OllamaEmbeddings(
    model=EMBED_NAME,
)

vector_store = Chroma(
    collection_name="example_collection",
    embedding_function = embeddings,
    persist_directory="./chroma_db",  # Where to save data locally, remove if not necessary
)

model = ChatOllama(
    model=LLM_NAME,
    temperature=0,
    num_ctx=8192 
)


# Define tools

@tool(response_format="content_and_artifact")
def retrieve_context(query: str):
    """Search the documentation/guide for specific query.
    
    Args:
        query: Search string to look up in the documents
    """
    print(f"DEBUG: Searching for '{query}'...")
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
    import subprocess
    
    # Security/Sanity check
    if not command.strip().lower().startswith("nmap"):
            return "Error: Command must start with 'nmap'."

    print(f"DEBUG: Executing Nmap command: {command}")
    
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


# Augment the LLM with tools
tools = [retrieve_context, execute_nmap_scan]
tools_by_name = {tool.name: tool for tool in tools}
model_with_tools = model.bind_tools(tools)

# Step 2: Define state

class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int

# Step 3: Define model node
def llm_call(state: dict):
    """LLM decides whether to call a tool or not"""

    return {
        "messages": [
            model_with_tools.invoke(
                [
                    SystemMessage(
                        content=LLM_SYSTEM_PROMPT
                    )
                ]
                + state["messages"]
            )
        ],
        "llm_calls": state.get('llm_calls', 0) + 1
    }


# Step 4: Define tool node
def tool_node(state: dict):
    """Performs the tool call"""

    result = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
    return {"messages": result}

def critic_node(state: MessagesState):
    messages = state["messages"]
    last_ai_message = messages[-1]

    # Find if there's an Nmap tool call to inspect
    nmap_call = next((tc for tc in last_ai_message.tool_calls if tc["name"] == "execute_nmap_scan"), None)
    
    if not nmap_call:
        return {"messages": []} # No command to criticize

    proposed_command = nmap_call["args"]["command"]
    
    # Retrieve the latest RAG context from message history
    rag_context = ""
    for m in reversed(messages):
        if isinstance(m, ToolMessage) and m.name == "retrieve_context":
            # m.content is the serialized string returned by your tool
            rag_context = m.content
            break

    # Invoke LLM as the Critic
    critic_response = model.invoke([
        SystemMessage(content=CRITIC_SYSTEM_PROMPT),
        HumanMessage(content=f"DOCUMENTATION CONTEXT:\n{rag_context}\n\nPROPOSED COMMAND: {proposed_command}")
    ])

    # Logic: If not valid, append the feedback to the conversation
    if "VALID" in critic_response.content.upper() and len(critic_response.content) < 15:
        return {"messages": []} # Pass
    else:
        # Construct failure feedback to force the LLM to rethink
        feedback = f"CRITICISM DETECTED:\n{critic_response.content}\n\nPlease correct the command and try again."
        return {"messages": [HumanMessage(content=feedback)]}

# Step 5: Define logic to determine whether to end

# Conditional edge function to route to the tool node or end based upon whether the LLM made a tool call
def should_continue(state: MessagesState) -> Literal["critic_node", END]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    messages = state["messages"]
    last_message = messages[-1]

    # If the LLM makes a tool call, then perform critic node
    if last_message.tool_calls:
        return "critic_node"

    # Otherwise, we stop (reply to the user)
    return END

# New router for the Critic's verdict
def route_after_critic(state: MessagesState) -> Literal["llm_call", "tool_node", END]:
    last_message = state["messages"][-1]
    
    # If the last message is the HumanMessage feedback from critic_node
    if isinstance(last_message, HumanMessage) and "CRITICISM DETECTED" in last_message.content:
        return "llm_call" # Loop back to fix
    
    # If the second to last message had tool calls and was cleared by critic
    return "tool_node"

# Step 6: Build agent

# Build workflow
agent_builder = StateGraph(MessagesState)

# Add nodes
agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("tool_node", tool_node)
agent_builder.add_node("critic_node", critic_node)

# Add edges to connect nodes
agent_builder.add_edge(START, "llm_call")

# Edge 1: LLM Call -> Critic (if tools) or END
agent_builder.add_conditional_edges(
    "llm_call",
    should_continue,
    {"critic_node": "critic_node", END: END}
)

# Edge 2: Critic -> LLM (to fix) or Tool (to execute)
agent_builder.add_conditional_edges(
    "critic_node",
    route_after_critic,
    {"llm_call": "llm_call", "tool_node": "tool_node", END: END}
)

# Edge 3: Tool -> LLM (to report results)
agent_builder.add_edge("tool_node", "llm_call")

# Compile the agent
agent = agent_builder.compile()

# Show the agent
try:
    graph_png = agent.get_graph(xray=True).draw_mermaid_png()
    with open("graph.png", "wb") as f:
        f.write(graph_png)
    print("Graph image saved to 'graph.png'")
except Exception as e:
    print(f"Could not save graph image: {e}")

query = \
"""I need to check if the host 127.0.0.1 is up and see which common ports are open.
# 1. Consult the Nmap guide to find the most efficient way to perform a 'Service Version Detection' scan.
# 2. Use the execute_nmap_scan tool to run the identified command against 127.0.0.1 and report the final output."""

# Invoke
messages = [HumanMessage(content=query)]
messages = agent.invoke({"messages": messages})
for m in messages["messages"]:
    m.pretty_print()