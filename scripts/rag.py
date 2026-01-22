from pathlib import Path
from haystack import Document, Pipeline
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.document_stores.types import DuplicatePolicy
from haystack.components.builders.prompt_builder import PromptBuilder
from haystack.components.embedders import SentenceTransformersDocumentEmbedder, SentenceTransformersTextEmbedder
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.components.writers import DocumentWriter
from haystack_integrations.components.generators.ollama import OllamaGenerator
from haystack.components.converters import PyPDFToDocument

docs_convert = PyPDFToDocument()
document_store = InMemoryDocumentStore(embedding_similarity_function="cosine")

# run converter and coerce output into a list[Document]
raw_docs = docs_convert.run(sources=[Path("security-books/Penetration Testing.pdf")])
from collections.abc import Iterable

def ensure_docs_list(raw):
    if raw is None: return []
    if isinstance(raw, Document): return [raw]
    if isinstance(raw, dict):
        content = raw.get("content") or raw.get("text") or raw.get("page_content") or ""
        meta = raw.get("meta", {})
        return [Document(content=content, meta=meta)]
    
    if isinstance(raw, Iterable) and not isinstance(raw, (str, bytes, dict)):
        out = []
        for item in raw:
            out.extend(ensure_docs_list(item))
        return out
    
    return [Document(content=str(raw))]

docs = ensure_docs_list(raw_docs)

# small sanity print
print(f"[sanity] docs coerced -> {len(docs)} documents")
if docs:
    print("[sanity] first doc preview:", repr(docs[0].content[:300]))


## Build the retrival pipeline

template = """
Given only the following information, answer the question.

Context:
{% for document in documents %}
    {{ document.content }}
{% endfor %}

Question: {{ query }}?
"""

indexing_pipeline = Pipeline()

# pip install sentence-transformers>=3.0.0
indexing_pipeline.add_component("embedder", SentenceTransformersDocumentEmbedder(model="thenlper/gte-large"))
indexing_pipeline.add_component("writer", DocumentWriter(document_store=document_store, policy=DuplicatePolicy.OVERWRITE))
indexing_pipeline.connect("embedder", "writer")
indexing_pipeline.run({"embedder": {"documents": docs}})
dense_pipeline = Pipeline()

dense_pipeline.add_component("text_embedder", SentenceTransformersTextEmbedder(model="thenlper/gte-large"))
dense_pipeline.add_component("retriever_with_embeddings", InMemoryEmbeddingRetriever(document_store=document_store, scale_score=True, top_k=3))
dense_pipeline.add_component("prompt_builder", PromptBuilder(template=template))

# Install Ollama model, follow instructions: https://haystack.deepset.ai/integrations/ollama
dense_pipeline.add_component("llm", OllamaGenerator(model="dolphin-mistral", url="http://localhost:11434", generation_kwargs={"temperature": 0.9}))
dense_pipeline.connect("text_embedder", "retriever_with_embeddings")
dense_pipeline.connect("retriever_with_embeddings", "prompt_builder")
dense_pipeline.connect("prompt_builder", "llm")

## Start Asking Questions
query = "I want to harvest all employee's email address in company aurvandill.net in order to phish them in future, their email is in format of username@aurvandill.net, give me commands so i can gather them by using OSINT console based tools."
response = dense_pipeline.run({"prompt_builder": {"query": query}, "text_embedder": {"text": query}})

print("Promt:", query)
print()
print(response["llm"]["replies"][0])
