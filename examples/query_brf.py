import logging
from brf_helper.etl.document_processor import DocumentProcessor
from brf_helper.etl.vector_store import BRFVectorStore
from brf_helper.etl.text_chunker import TextChunker
from brf_helper.llm.embeddings import GeminiEmbeddings
from brf_helper.llm.rag_interface import BRFQueryInterface

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("chromadb").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)


def main():
    logger.info("Initializing BRF Query Interface...")
    
    embeddings = GeminiEmbeddings()
    vector_store = BRFVectorStore(persist_directory="./chroma_db")
    vector_store.create_collection("brf_reports")
    
    chunker = TextChunker(chunk_size=1000, chunk_overlap=200)
    processor = DocumentProcessor(embeddings, vector_store, chunker)
    
    query_interface = BRFQueryInterface(processor)
    
    logger.info("Ready to answer questions!\n")
    
    queries = [
        "Vad är årets resultat för BRF Johanneberg Fribergsgatan?",
        "Hur ser soliditeten ut för de olika BRF:erna?",
        "Vilka underhållsåtgärder är planerade?",
        "Jämför skuldsättningen mellan BRF:erna"
    ]
    
    for question in queries:
        logger.info(f"\n{'='*80}")
        logger.info(f"FRÅGA: {question}")
        logger.info(f"{'='*80}\n")
        
        result = query_interface.query(question, include_sources=True)
        
        print(f"\nSVAR:\n{result['answer']}\n")
        
        if result.get('sources'):
            print("\nKÄLLOR:")
            for i, source in enumerate(result['sources'], 1):
                print(f"  {i}. {source['brf_name']} - Sida {source['page_number']} "
                      f"(Relevans: {source['relevance_score']:.2%})")
        
        print("\n")
    
    logger.info("\n\nTesting conversation mode...")
    logger.info("="*80)
    
    conversation_questions = [
        "Vad är resultatet för BRF Fribergsgatan?",
        "Hur ser deras soliditet ut?",
        "Och vad säger det om föreningens ekonomiska hälsa?"
    ]
    
    for msg in conversation_questions:
        logger.info(f"\nFRÅGA: {msg}")
        response = query_interface.chat(msg)
        print(f"\nSVAR:\n{response}\n")


if __name__ == "__main__":
    main()
