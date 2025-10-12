import pytest
from fastapi.testclient import TestClient
from brf_helper.api.main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_check(self):
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestCollectionInfoEndpoint:
    def test_collection_info(self):
        response = client.get("/collection/info")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "count" in data
        assert isinstance(data["count"], int)


class TestQueryEndpoint:
    def test_query_without_sources(self):
        response = client.post(
            "/query",
            json={
                "question": "Vad är årets resultat?",
                "include_sources": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "question" in data
        assert "answer" in data
        assert data["question"] == "Vad är årets resultat?"
        assert isinstance(data["answer"], str)
        assert len(data["answer"]) > 0
    
    def test_query_with_sources(self):
        response = client.post(
            "/query",
            json={
                "question": "Hur ser ekonomin ut?",
                "include_sources": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "sources" in data
        if data["sources"]:
            source = data["sources"][0]
            assert "brf_name" in source
            assert "relevance_score" in source
    
    def test_query_with_brf_filter(self):
        response = client.post(
            "/query",
            json={
                "question": "Vad är resultatet?",
                "brf_name": "brf_fribergsgatan_8_2024",
                "include_sources": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["brf_name"] == "brf_fribergsgatan_8_2024"
    
    def test_query_missing_question(self):
        response = client.post(
            "/query",
            json={"include_sources": True}
        )
        
        assert response.status_code == 422


class TestChatEndpoint:
    def test_chat_message(self):
        response = client.post(
            "/chat",
            json={"message": "Vad är soliditeten?"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "response" in data
        assert data["message"] == "Vad är soliditeten?"
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0
    
    def test_chat_with_brf_filter(self):
        response = client.post(
            "/chat",
            json={
                "message": "Hur mycket är avgiften?",
                "brf_name": "brf_volrat_tham_2024"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
    
    def test_chat_missing_message(self):
        response = client.post(
            "/chat",
            json={}
        )
        
        assert response.status_code == 422


class TestUploadEndpoint:
    def test_upload_non_pdf(self):
        response = client.post(
            "/upload",
            files={"file": ("test.txt", b"test content", "text/plain")}
        )
        
        assert response.status_code == 400
        assert "Only PDF files are allowed" in response.json()["detail"]
