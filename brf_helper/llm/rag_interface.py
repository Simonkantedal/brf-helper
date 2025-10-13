import logging
from brf_helper.llm.chat_model import GeminiChat
from brf_helper.etl.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)


class BRFQueryInterface:
    def __init__(
        self,
        document_processor: DocumentProcessor,
        chat_model: GeminiChat = None,
        n_results: int = 5,
        use_hybrid: bool = True
    ):
        self.document_processor = document_processor
        self.n_results = n_results
        self.use_hybrid = use_hybrid
        
        system_instruction = """
        Du är en expert på svenska bostadsrättsföreningar (BRF) och deras ekonomi.
        Din uppgift är att hjälpa användare att förstå och analysera BRF:ers årsredovisningar.

            När du svarar:
            - Använd alltid informationen från de tillhandahållna dokumenten
            - Svara på svenska
            - Var specifik och hänvisa till siffror när det är möjligt
            - Om du inte hittar informationen i kontexten, säg det tydligt
            - Förklara ekonomiska termer på ett enkelt sätt
            - Jämför gärna olika BRF:er om användaren frågar om flera

            Fokusera på:
            - Ekonomisk status (resultat, soliditet, skuldsättning)
            - Årsavgifter
            - Underhållsbehov och planer
            - Föreningens verksamhet
        """
        
        self.chat_model = chat_model or GeminiChat(
            system_instruction=system_instruction,
            temperature=0.3
        )
    
    def query(
        self,
        question: str,
        brf_name: str = None,
        include_sources: bool = True
    ) -> dict:
        logger.info(f"Processing query: {question}")
        
        search_results = self.document_processor.search(
            query=question,
            n_results=self.n_results,
            brf_name=brf_name,
            use_hybrid=self.use_hybrid
        )
        
        context = self._build_context(search_results)     
        prompt = self._build_prompt(question, context)
        answer = self.chat_model.generate_response(prompt)
        
        response = {
            "question": question,
            "answer": answer,
            "brf_name": brf_name
        }
        
        if include_sources:
            response["sources"] = self._format_sources(search_results)
        
        logger.info("Query processed successfully")
        return response
    
    def chat(
        self,
        message: str,
        brf_name: str = None
    ) -> str:
        search_results = self.document_processor.search(
            query=message,
            n_results=self.n_results,
            brf_name=brf_name,
            use_hybrid=self.use_hybrid
        )
        
        context = self._build_context(search_results)
        
        enhanced_message = f"""
        Baserat på följande kontext från BRF-dokument, svara på användarens fråga:

        KONTEXT:
        {context}

        ANVÄNDARENS FRÅGA:
        {message}
        """
        
        if not self.chat_model.chat_session:
            self.chat_model.start_chat()
        
        answer = self.chat_model.send_message(enhanced_message)
        
        return answer
    
    def _build_context(self, search_results: dict) -> str:
        context_parts = []
        
        for doc, metadata in zip(
            search_results["documents"],
            search_results["metadatas"]
        ):
            brf = metadata.get("brf_name", "Okänd BRF")
            page = metadata.get("page_number", "?")
            
            context_parts.append(
                f"[BRF: {brf}, Sida: {page}]\n{doc}\n"
            )
        
        return "\n---\n".join(context_parts)
    
    def _build_prompt(self, question: str, context: str) -> str:
        return f"""
        Baserat på följande information från BRF-dokument, besvara frågan.

        KONTEXT FRÅN DOKUMENT:
        {context}

        FRÅGA:
        {question}

        SVAR:
        """
    
    def _format_sources(self, search_results: dict) -> list[dict]:
        sources = []
        
        for metadata, distance in zip(
            search_results["metadatas"],
            search_results["distances"]
        ):
            sources.append({
                "brf_name": metadata.get("brf_name", "Okänd"),
                "page_number": metadata.get("page_number"),
                "relevance_score": float(1 - distance)
            })
        
        return sources
    
    def get_conversation_history(self) -> list[dict[str, str]]:
        return self.chat_model.get_history()
    
    def clear_conversation(self) -> None:
        self.chat_model.start_chat()
        logger.info("Conversation cleared")
