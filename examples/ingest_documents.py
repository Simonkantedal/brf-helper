import logging
from pathlib import Path
from brf_helper.etl.document_processor import DocumentProcessor
from brf_helper.etl.vector_store import BRFVectorStore
from brf_helper.etl.text_chunker import TextChunker
from brf_helper.llm.embeddings import GeminiEmbeddings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("chromadb").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)


def main():
    logger.info("Initializing components...")
    
    embeddings = GeminiEmbeddings()
    vector_store = BRFVectorStore(persist_directory="./chroma_db")
    vector_store.create_collection("brf_reports", reset=True)
    
    chunker = TextChunker(chunk_size=1000, chunk_overlap=200)
    processor = DocumentProcessor(embeddings, vector_store, chunker)
    
    logger.info("Processing PDFs from data directory...")
    data_dir = Path("data")
    results = processor.process_directory(data_dir)
    
    logger.info("Ingestion complete!")
    for result in results:
        logger.info(f"BRF: {result['brf_name']}, Pages: {result['num_pages']}, Chunks: {result['num_chunks']}")
    
    info = vector_store.get_collection_info()
    logger.info(f"Total documents in collection: {info['count']}")
    
    logger.info("Testing search...")
    query = "Vad är årets resultat?"
    logger.info(f"Query: '{query}'")
    
    search_results = processor.search(query, n_results=3)
    
    logger.info("Top results:")
    for i, (doc, metadata, distance) in enumerate(zip(
        search_results["documents"],
        search_results["metadatas"],
        search_results["distances"]
    ), 1):
        logger.info(
            f"{i}. Distance: {distance:.4f}, BRF: {metadata.get('brf_name', 'N/A')}, "
            f"Page: {metadata.get('page_number', 'N/A')}"
        )
        logger.debug(f"   Text: {doc[:200]}...")


if __name__ == "__main__":
    main()
