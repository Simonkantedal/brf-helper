import os
import time
from typing import List
import google.generativeai as genai
from google.api_core import exceptions
from dotenv import load_dotenv

load_dotenv()


class GeminiEmbeddings:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "models/text-embedding-004",
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment or provided")
        
        genai.configure(api_key=self.api_key)
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def _embed_with_retry(self, content: str, task_type: str) -> List[float]:
        for attempt in range(self.max_retries):
            try:
                result = genai.embed_content(
                    model=self.model,
                    content=content,
                    task_type=task_type
                )
                return result["embedding"]
            except exceptions.InternalServerError as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    time.sleep(wait_time)
                else:
                    raise
            except Exception as e:
                raise
    
    def embed_text(self, text: str) -> List[float]:
        return self._embed_with_retry(text, "retrieval_document")
    
    def embed_query(self, query: str) -> List[float]:
        return self._embed_with_retry(query, "retrieval_query")
    
    def embed_batch(self, texts: List[str], delay: float = 0.1) -> List[List[float]]:
        embeddings = []
        for text in texts:
            embeddings.append(self.embed_text(text))
            time.sleep(delay)
        return embeddings
