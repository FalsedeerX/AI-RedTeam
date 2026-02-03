import os
from langchain_community.document_loaders import PDFPlumberLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_chroma import Chroma

LLM_NAME = "huihui_ai/qwen3-vl-abliterated"
EMBED_NAME = "mxbai-embed-large"  
AGENT_MODE = True 
DOCS_PATH = "./docs/"

model = ChatOllama(
    model=LLM_NAME,
    temperature=0
)

docs = []

files = os.listdir(DOCS_PATH)
for file in files:
    if not file.endswith(".pdf"):
        continue
    loader = PDFPlumberLoader(os.path.join(DOCS_PATH, file))
    doc = loader.load()[0]
    print(f"Total characters: {len(doc.page_content)}")
    # print(doc.metadata)  # Debug Use only
    docs.append(doc)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,  # chunk size (characters)
    chunk_overlap=200,  # chunk overlap (characters)
    add_start_index=True,  # track index in original document
)
all_splits = text_splitter.split_documents(docs)

print(f"Split blog post into {len(all_splits)} sub-documents.")

embeddings = OllamaEmbeddings(
    model=EMBED_NAME,
)

vector_store = Chroma(
    collection_name="example_collection",
    embedding_function = embeddings,
    persist_directory="./chroma_db",  # Where to save data locally, remove if not necessary
)

vector_store.add_documents(documents=all_splits)

if AGENT_MODE:
    print("Running in agent mode...")

    from langchain.tools import tool
    from langchain.agents import create_agent
    from langchain_community.tools import DuckDuckGoSearchRun
    import os

    @tool(response_format="content_and_artifact")
    def retrieve_context(query: str):
        """Retrieve information to help answer a query."""
        retrieved_docs = vector_store.similarity_search(query, k=2)
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

    tools = [retrieve_context, duckduckgo_search_tool]
    # If desired, specify custom instructions
    prompt = (
        "You have access to a tool that retrieves context from pdfs under doc folder in this project. "
        "Use the tool to help answer user queries."
    )
    agent = create_agent(model, tools, system_prompt=prompt)


    query = (
        "What is the scope of AI RedTeam?\n\n"
        "Does the document mention anything about penetration testing?\n\n"
        "Who is Trump's vice president?"
    )

    for event in agent.stream(
        {"messages": [{"role": "user", "content": query}]},
        stream_mode="values",
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