from pathlib import Path
import chromadb
from chromadb.config import Settings
from typing import Optional, List, Dict
from brf_helper.etl.hybrid_retrieval import HybridRetriever


class BRFVectorStore:
    def __init__(self, persist_directory: str = "./chroma_db", enable_hybrid: bool = True):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.collection = None
        self.enable_hybrid = enable_hybrid
        self.hybrid_retriever = None
    
    def create_collection(self, name: str, reset: bool = False) -> None:
        if reset:
            try:
                self.client.delete_collection(name=name)
            except (ValueError, Exception):
                pass
        
        self.collection = self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Initialize hybrid retriever if enabled
        if self.enable_hybrid:
            self.hybrid_retriever = HybridRetriever(self)
    
    def add_documents(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict] | None = None,
        ids: list[str] | None = None
    ) -> None:
        if not self.collection:
            raise ValueError("Collection not created. Call create_collection first.")
        
        if ids is None:
            ids = [f"doc_{i}" for i in range(len(texts))]
        
        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        # Rebuild BM25 index if hybrid retrieval is enabled
        if self.enable_hybrid and self.hybrid_retriever:
            self.hybrid_retriever.build_bm25_index(force_rebuild=True)
    
    def search(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        where: dict | None = None,
        query_text: str = None,
        use_hybrid: bool = None
    ) -> dict:
        if not self.collection:
            raise ValueError("Collection not created. Call create_collection first.")
        
        # Determine if hybrid search should be used
        if use_hybrid is None:
            use_hybrid = self.enable_hybrid
        
        # Use hybrid search if enabled and query text is provided
        if use_hybrid and self.hybrid_retriever and query_text:
            return self.hybrid_retriever.search(
                query=query_text,
                query_embedding=query_embedding,
                n_results=n_results,
                where=where
            )
        
        # Fall back to vector-only search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where
        )
        
        return {
            "documents": results["documents"][0],
            "metadatas": results["metadatas"][0],
            "distances": results["distances"][0],
            "ids": results["ids"][0]
        }
    
    def get_collection_info(self) -> dict:
        if not self.collection:
            raise ValueError("Collection not created.")
        
        count = self.collection.count()
        return {
            "name": self.collection.name,
            "count": count
        }
    
    def delete_collection(self, name: str) -> None:
        self.client.delete_collection(name=name)
        self.collection = None
