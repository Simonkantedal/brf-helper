import os
from typing import List, Dict, Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


class GeminiChat:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-2.0-flash-exp",
        temperature: float = 0.7,
        system_instruction: str | None = None
    ):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment or provided")
        
        genai.configure(api_key=self.api_key)
        
        generation_config = {
            "temperature": temperature,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
        
        self.model = genai.GenerativeModel(
            model_name=model,
            generation_config=generation_config,
            system_instruction=system_instruction
        )
        
        self.chat_session = None
    
    def start_chat(self, history: List[Dict[str, str]] = None) -> None:
        formatted_history = []
        if history:
            for msg in history:
                formatted_history.append({
                    "role": msg["role"],
                    "parts": [msg["content"]]
                })
        
        self.chat_session = self.model.start_chat(history=formatted_history)
    
    def send_message(self, message: str) -> str:
        if not self.chat_session:
            self.start_chat()
        
        response = self.chat_session.send_message(message)
        return response.text
    
    def generate_response(self, prompt: str) -> str:
        response = self.model.generate_content(prompt)
        return response.text
    
    def get_history(self) -> List[Dict[str, str]]:
        if not self.chat_session:
            return []
        
        history = []
        for msg in self.chat_session.history:
            history.append({
                "role": msg.role,
                "content": msg.parts[0].text
            })
        return history
