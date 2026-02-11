from langchain_ollama import OllamaEmbeddings
from .config import config

def get_embeddings():
    """
    Returns the configured embedding model.
    Using OllamaEmbeddings as per the user's demo.
    """
    return OllamaEmbeddings(
        model=config.EMBEDDING_MODEL_NAME,
    )
