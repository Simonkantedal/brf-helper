import pytest
import os
from brf_helper.llm.embeddings import GeminiEmbeddings


@pytest.fixture
def api_key():
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        pytest.skip("GOOGLE_API_KEY not set")
    return key


@pytest.fixture
def embeddings(api_key):
    return GeminiEmbeddings(api_key=api_key)


class TestGeminiEmbeddings:
    def test_initialization_with_api_key(self, api_key):
        embeddings = GeminiEmbeddings(api_key=api_key)
        assert embeddings.api_key == api_key
        assert embeddings.model == "models/text-embedding-004"
    
    def test_initialization_without_api_key(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        
        with pytest.raises(ValueError, match="GOOGLE_API_KEY not found"):
            GeminiEmbeddings()
    
    @pytest.mark.skipif(not os.getenv("GOOGLE_API_KEY"), reason="GOOGLE_API_KEY not set")
    def test_embed_text(self, embeddings):
        text = "This is a test document about Swedish BRF reports"
        embedding = embeddings.embed_text(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)
    
    @pytest.mark.skipif(not os.getenv("GOOGLE_API_KEY"), reason="GOOGLE_API_KEY not set")
    def test_embed_query(self, embeddings):
        query = "What is the financial status?"
        embedding = embeddings.embed_query(query)
        
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)
    
    @pytest.mark.skipif(not os.getenv("GOOGLE_API_KEY"), reason="GOOGLE_API_KEY not set")
    def test_embed_batch(self, embeddings):
        texts = [
            "First test document",
            "Second test document",
            "Third test document"
        ]
        embeddings_list = embeddings.embed_batch(texts)
        
        assert len(embeddings_list) == 3
        assert all(isinstance(emb, list) for emb in embeddings_list)
        assert all(len(emb) > 0 for emb in embeddings_list)
