from pathlib import Path
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings


class BRFVectorStore:
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.collection = None
    
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
    
    def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None
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
    
    def search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict] = None
    ) -> Dict:
        if not self.collection:
            raise ValueError("Collection not created. Call create_collection first.")
        
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
    
    def get_collection_info(self) -> Dict:
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
