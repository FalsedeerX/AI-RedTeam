import shutil
import os
import glob
from typing import List
from langchain_chroma import Chroma
from langchain_community.document_loaders import PDFPlumberLoader, TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from .config import config
from .embeddings import get_embeddings


class RAGVectorStore:
    def __init__(self):
        self._vector_store_instance = None

    def get_vector_store(self):
        """
        Returns the Chroma vector store instance.
        Returns:
            Chroma: The vector store instance.
        """
        if self._vector_store_instance is None:
            embedding_func = get_embeddings()
            self._vector_store_instance = Chroma(
                collection_name=config.COLLECTION_NAME,
                embedding_function=embedding_func,
                persist_directory=config.CHROMA_PERSIST_DIRECTORY
            )
        return self._vector_store_instance

    def load_documents_from_directory(self, src: str) -> List[Document]:
        """
        Loads documents from the specified directory.
        Args:
            src: Directory path to load documents from.
        Returns:
            List[Document]: List of loaded documents.
        """
        documents = []
        
        # Check if directory exists
        if not os.path.exists(src):
            print(f"Directory {src} does not exist.")
            return []

        # Load PDFs
        pdf_pattern = os.path.join(src, "**/*.pdf")
        pdf_files = glob.glob(pdf_pattern, recursive=True)
        for pdf_path in pdf_files:
            try:
                loader = PDFPlumberLoader(pdf_path)
                # print(loader.load()) # Optional debug
                documents.extend(loader.load())
                print(f"Loaded {pdf_path}")
            except Exception as e:
                print(f"Error loading PDF {pdf_path}: {e}")

        # Load Markdown
        md_pattern = os.path.join(src, "**/*.md")
        md_files = glob.glob(md_pattern, recursive=True)
        for md_path in md_files:
            try:
                loader = TextLoader(md_path, encoding='utf-8')
                documents.extend(loader.load())
                print(f"Loaded {md_path}")
            except Exception as e:
                print(f"Error loading Markdown {md_path}: {e}")

        return documents

    def ingest_documents(self, src: str):
        """
        Ingests documents from a directory into the vector store.
        Args:
            src: Directory path to load documents from.
        """
        print(f"Loading documents from {src}...")
        docs = self.load_documents_from_directory(src)
        
        if not docs:
            print("No documents found to ingest.")
            return

        print(f"Splitting {len(docs)} documents...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP
        )
        
        splits = text_splitter.split_documents(docs)
        print(f"Created {len(splits)} chunks.")
        
        print("Adding to vector store...")
        vector_store = self.get_vector_store()
        vector_store.add_documents(documents=splits)
        print("Ingestion complete.")

    def clear_vector_store(self):
        """
        Clears the existing vector store data. 
        """
        if os.path.exists(config.CHROMA_PERSIST_DIRECTORY):
            try:
                shutil.rmtree(config.CHROMA_PERSIST_DIRECTORY)
                print("Vector store cleared.")
                # Reset instance after clearing
                self._vector_store_instance = None
            except Exception as e:
                print(f"Error clearing vector store: {e}")

# Create a singleton instance for backward compatibility or direct import usage
vector_store_service = RAGVectorStore()

def get_vector_store():
    return vector_store_service.get_vector_store()

def ingest_documents(src: str):
    return vector_store_service.ingest_documents(src)

def clear_vector_store():
    return vector_store_service.clear_vector_store()
