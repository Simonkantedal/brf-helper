import pytest
from pathlib import Path
import shutil
from brf_helper.etl.vector_store import BRFVectorStore


@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "test_chroma_db")


@pytest.fixture
def vector_store(temp_db_path):
    store = BRFVectorStore(persist_directory=temp_db_path)
    yield store
    if Path(temp_db_path).exists():
        shutil.rmtree(temp_db_path)


class TestBRFVectorStore:
    def test_initialization(self, vector_store, temp_db_path):
        assert vector_store.persist_directory == Path(temp_db_path)
        assert vector_store.persist_directory.exists()
    
    def test_create_collection(self, vector_store):
        vector_store.create_collection("test_collection")
        
        assert vector_store.collection is not None
        assert vector_store.collection.name == "test_collection"
    
    def test_add_documents(self, vector_store):
        vector_store.create_collection("test_collection")
        
        texts = ["This is a test document", "Another test document"]
        embeddings = [[0.1] * 768, [0.2] * 768]
        metadatas = [{"source": "test1"}, {"source": "test2"}]
        
        vector_store.add_documents(
            texts=texts,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        info = vector_store.get_collection_info()
        assert info["count"] == 2
    
    def test_search(self, vector_store):
        vector_store.create_collection("test_collection")
        
        texts = ["Swedish BRF annual report", "Financial statement"]
        embeddings = [[0.1] * 768, [0.2] * 768]
        
        vector_store.add_documents(texts=texts, embeddings=embeddings)
        
        query_embedding = [0.15] * 768
        results = vector_store.search(query_embedding, n_results=1)
        
        assert len(results["documents"]) == 1
        assert results["documents"][0] in texts
    
    def test_collection_not_created_error(self, vector_store):
        with pytest.raises(ValueError, match="Collection not created"):
            vector_store.add_documents([], [])
    
    def test_reset_collection(self, vector_store):
        vector_store.create_collection("test_collection")
        vector_store.add_documents(
            texts=["test"],
            embeddings=[[0.1] * 768]
        )
        
        vector_store.create_collection("test_collection", reset=True)
        info = vector_store.get_collection_info()
        assert info["count"] == 0
