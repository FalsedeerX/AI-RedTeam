"""RAG Node — standalone knowledge-retrieval node for the agent graph.

Thinking nodes (Planner, Tactician, Critic, Analyst) request a RAG search
by setting ``rag_query`` and ``rag_reason`` in the graph state.  This node
performs a vector-store similarity search, uses an LLM to extract the most
relevant excerpts, and appends the result to the message history before
the graph routes back to the calling node.
"""

import re

from langchain_core.messages import HumanMessage, SystemMessage

from .config import config
from .vector_store import get_vector_store


def _strip_think_tags(text: str) -> str:
    """Remove qwen3 ``<think>`` artifacts from *text*."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"</?think>?", "", text)
    text = re.sub(r"/think\b", "", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


class RAGNode:
    """Performs vector-store retrieval + LLM-based excerpt selection.

    Parameters
    ----------
    llm_model
        A LangChain-compatible chat model used for summarising / selecting
        the most relevant fragments from retrieved documents.
    """

    def __init__(self, llm_model):
        self.llm = llm_model

    def __call__(self, state: dict) -> dict:
        """Execute the RAG search and return results to the calling node."""
        query = state.get("rag_query", "")
        reason = state.get("rag_reason", "")

        if not query:
            return {
                "messages": [HumanMessage(content="[RAG] No search query provided.")],
                "rag_query": "",
                "rag_reason": "",
            }

        # --- 1. Vector-store similarity search ---
        vector_store = get_vector_store()
        docs = vector_store.similarity_search(query, k=config.RETRIEVER_K)

        if not docs:
            return {
                "messages": [HumanMessage(
                    content=f"[RAG SEARCH RESULT — query: '{query}']\nNo relevant documents found."
                )],
                "rag_query": "",
                "rag_reason": "",
            }

        raw_context = "\n\n---\n\n".join(
            f"Source: {doc.metadata}\n{doc.page_content}" for doc in docs
        )

        # --- 2. LLM-based excerpt selection ---
        prompt = (
            f"SEARCH QUERY: {query}\n"
            f"SEARCH REASON: {reason}\n\n"
            f"RETRIEVED DOCUMENTS:\n{raw_context}"
        )

        response = self.llm.invoke([
            SystemMessage(content=config.RAG_NODE_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        summary = _strip_think_tags(response.content)

        return {
            "messages": [HumanMessage(
                content=f"[RAG SEARCH RESULT — query: '{query}']\n{summary}"
            )],
            "rag_query": "",
            "rag_reason": "",
        }
