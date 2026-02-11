# Create a test script to verify the RAG Agent implementation
# Must be run from the project root or Ensure 'service' is in path
# Usage: python service/test_agent.py

import sys
import os
from langchain_core.messages import HumanMessage
from redteam_agent import ingest_documents, get_agent, config
from redteam_agent.vector_store import clear_vector_store

# Add current directory to path so we can import 'rag' package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    print("=== AI RedTeam Agent Test ===")
    print(f"Configuration:")
    print(f" - Embedder: {config.EMBEDDING_MODEL_NAME}")
    print(f" - LLM: {config.LLM_MODEL_NAME}")
    print(f" - ChromaDB: {config.CHROMA_PERSIST_DIRECTORY}")
    
    print(f"\n[1] Check/Ingest Documents")
    print(f"Target directory: {config.DOCS_SOURCE_DIRECTORY}")
    choice = input("Do you want to run document ingestion? (y/n/c[lear]): ").strip().lower()
    
    if choice == 'y':
        try:
            ingest_documents(config.DOCS_SOURCE_DIRECTORY)
        except Exception as e:
            print(f"Ingestion failed: {e}")
            return
    elif choice == 'c':
        print("Clearing vector store...")
        clear_vector_store()
        print("Ingesting new documents...")
        ingest_documents(config.DOCS_SOURCE_DIRECTORY)
    else:
        print("Skipping ingestion.")

    print(f"\n[2] Run Agent Test")
    print("Please ensure Ollama is running locally (ollama serve).")
    
    default_query = "I need to check if the host 127.0.0.1 is up. Find the most efficient way to perform a 'Service Version Detection' scan from the guides and execute it."
    query = input(f"Enter a test query (default: '{default_query}'): ").strip()
    if not query:
        query = default_query
        
    try:
        print("Initializing Agent Graph...")
        agent = get_agent()
        graph = agent.app
        
        print("Saving graph structure as image... (agent_graph.png)")
        agent.save_graph_image("agent_graph.png")
        
        print(f"\nQuerying: {query}")
        print("-" * 50)
        
        # Invoke the graph with streaming to show progress
        initial_state = {"messages": [HumanMessage(content=query)], "llm_calls": 0}
        config_run = {"recursion_limit": 20} # Safety limit
        
        for event in graph.stream(initial_state, config=config_run):
            for node_name, values in event.items():
                print(f"\n--- Node: {node_name} ---") 
                if "messages" in values:
                    for m in values["messages"]:
                        # Identify message type
                        msg_type = m.type
                        content = m.content
                        
                        # Print based on message type
                        if msg_type == "ai":
                            print(f"[AI]: {content}")
                            if hasattr(m, 'tool_calls') and m.tool_calls:
                                for tc in m.tool_calls:
                                    print(f"  [Tool Call Request]: {tc['name']}")
                                    print(f"  Arguments: {tc['args']}")
                        elif msg_type == "tool":
                            print(f"[Tool Output - {m.name}]:")
                            # Truncate long tool outputs
                            if len(content) > 500:
                                print(f"{content[:500]}... [truncated]")
                            else:
                                print(content)
                        elif msg_type == "human":
                            # This usually comes from the Critic in this graph
                            print(f"[Critic Feedback]: {content}")
                        else:
                            print(f"[{msg_type}]: {content}")
                            
        print("-" * 50)
        print("Agent execution sequence completed.")
    except Exception as e:
        print(f"\nError during execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
