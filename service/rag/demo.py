import os
from langchain_community.document_loaders import PDFPlumberLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import shutil

# LLM_NAME = "huihui_ai/qwen3-vl-abliterated"
LLM_NAME = "qwen3:8b"
EMBED_NAME = "bge-m3"
# EMBED_NAME = "nomic-embed-text"
# EMBED_NAME = "mxbai-embed-large"  
# EMBED_NAME = "mixedbread-ai/mxbai-embed-large-v1" 
# EMBED_NAME = "sentence-transformers/all-MiniLM-L6-v2" # 更快但在中文/長文表現較差的替代方案
DELETE_DATABASE_IF_EXISTS = False
STORE_DOCUMENTS = False
AGENT_MODE = True 
DOCS_PATH = "./service/rag/lib/"


model = ChatOllama(
    model=LLM_NAME,
    temperature=0,
    num_ctx=8192 
)

if DELETE_DATABASE_IF_EXISTS:
    if os.path.exists("./chroma_db"):
        shutil.rmtree("./chroma_db")

embeddings = OllamaEmbeddings(
    model=EMBED_NAME,
)

vector_store = Chroma(
    collection_name="example_collection",
    embedding_function = embeddings,
    persist_directory="./chroma_db",  # Where to save data locally, remove if not necessary
)

if STORE_DOCUMENTS:
    docs = []

    files = os.listdir(DOCS_PATH)
    for file in files:
        if not file.endswith(".pdf"):
            continue
        loader = PDFPlumberLoader(os.path.join(DOCS_PATH, file))
        doc = loader.load()
        print(f"Loaded {file}")
        print(f"Total pages: {len(doc)}")
        # print(doc.metadata)  # Debug Use only
        docs.extend(doc)


    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=300,
        add_start_index=True,
    )
    all_splits = text_splitter.split_documents(docs)

    print(f"Split blog post into {len(all_splits)} sub-documents.")

    vector_store.add_documents(documents=all_splits)

if AGENT_MODE:
    print("Running in agent mode...")

    from langchain.tools import tool
    from langchain.agents import create_agent
    from langchain_community.tools import DuckDuckGoSearchRun
    import os

    @tool(response_format="content_and_artifact")
    def retrieve_context(query: str):
        """Search the documentation/guide for specific topics.
        
        Args:
            query: The search string to look up in the docs (e.g. 'timing templates', 'inter-probe delay').
        """
        print(f"DEBUG: Searching for '{query}'...")
        retrieved_docs = vector_store.similarity_search(query, k=5)
        
        serialized = "\n\n".join(
            (f"Source: {doc.metadata}\nContent: {doc.page_content}")
            for doc in retrieved_docs
        )
        return serialized, retrieved_docs    

    @tool
    def duckduckgo_search_tool(query: str):
        """Use DuckDuckGo Search to find relevant information."""
        search = DuckDuckGoSearchRun()
        results = search.run(query)
        return results

    tools = [retrieve_context] #, duckduckgo_search_tool
    # If desired, specify custom instructions
    prompt = (
        """### Role
        Security Assistant: Derive configs **strictly** from `retrieve_context`.

        ### Rules
        1. **Tool Mandatory**: You Must call `retrieve_context` for ALL technical queries BEFORE answering. Do not use internal knowledge for specs.
        2. **Fact Supremacy**: Context > Internal memory. Follow documentation 100%.
        3. **Logic Check**: Resolve flag conflicts (Mutual Exclusivity) and obey all mathematical/range limits.
        4. **Safety**: Warn for high-risk tasks and state: "Execution pending user approval."
        5. **Humility**: If info is missing or structural (TOC), state "Information not found." No guessing.
        6. Before generating the command, explicitly list which scan types are DISALLOWED for the requested technique based on the guide.

        ### Output Format
        - **Flag**: [Flag Name]
        - **Explanation**: [Brief summary from manual]
        - **Command**: 
        ```bash
        [Complete Command]"""
    )
    # agent = create_agent(model, tools, system_prompt=prompt)
    agent = create_agent(model, tools, system_prompt=prompt)


    query = (
        # """Consult the Nmap Official Guide regarding 'Timing and Performance'. I need to scan the host 192.168.1.100 as aggressively as possible, but I must set a specific delay of 200 milliseconds between each probe to stay under a specific detection threshold.
        # 1. Identify the exact flag mentioned in the guide for 'inter-probe delay'.
        # 2. Generate and execute the Nmap command using this flag.
        # 3. Report the scan results once the tool execution is complete."""
        # """I need to bypass a firewall that inspects large packets. Consult the Nmap Guide regarding 'Fragmenting Packets'.
        # 1. Find the flag used to specify a custom MTU (Maximum Transmission Unit) for the scan.
        # 2. According to the manual, what is the specific mathematical requirement for the offset value provided to this flag?
        # 3. Generate a command to scan 192.168.1.1 using an offset of 24."""
        # """I need to use fragmentation to bypass a firewall on 192.168.1.1. Choose the most appropriate scan type that supports fragmentation according to the guide and generate the command with --mtu 16."""
        """Perform an OS Detection (-O) scan on 192.168.1.1 but the firewall blocks all standard fragmentation. Try using custom fragmentation with an offset of 32, and ensure you bypass Linux kernel defragmentation by using the raw ethernet option as suggested in the guide."""
    )

    for event in agent.stream(
        {"messages": [{"role": "user", "content": query}]},
        stream_mode="values"#, debug=True
    ):
        event["messages"][-1].pretty_print()

else:
    print("Running in standard mode...")

    from langchain.agents.middleware import dynamic_prompt, ModelRequest
    from langchain.agents import create_agent

    @dynamic_prompt
    def prompt_with_context(request: ModelRequest) -> str:
        """Inject context into state messages."""
        last_query = request.state["messages"][-1].text
        retrieved_docs = vector_store.similarity_search(last_query)

        docs_content = "\n\n".join(doc.page_content for doc in retrieved_docs)

        system_message = (
            "You are a helpful assistant. Use the following context in your response:"
            f"\n\n{docs_content}"
        )

        return system_message

    agent = create_agent(model, tools=[], middleware=[prompt_with_context])

    query = (
        "What is the scope of AI RedTeam?\n\n"
        "Does the document mention anything about penetration testing?\n\n"
        "Can I use AI RedTeam to attack someone?"
    )

    for step in agent.stream(
        {"messages": [{"role": "user", "content": query}]},
        stream_mode="values",
    ):
        step["messages"][-1].pretty_print()