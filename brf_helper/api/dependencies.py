import logging
from functools import lru_cache
from brf_helper.etl.document_processor import DocumentProcessor
from brf_helper.etl.vector_store import BRFVectorStore
from brf_helper.etl.text_chunker import TextChunker
from brf_helper.llm.embeddings import GeminiEmbeddings
from brf_helper.llm.rag_interface import BRFQueryInterface

logger = logging.getLogger(__name__)


@lru_cache()
def get_embeddings() -> GeminiEmbeddings:
    logger.info("Initializing GeminiEmbeddings")
    return GeminiEmbeddings()


@lru_cache()
def get_vector_store() -> BRFVectorStore:
    logger.info("Initializing BRFVectorStore")
    vector_store = BRFVectorStore(persist_directory="./chroma_db")
    vector_store.create_collection("brf_reports")
    return vector_store


@lru_cache()
def get_document_processor() -> DocumentProcessor:
    logger.info("Initializing DocumentProcessor")
    embeddings = get_embeddings()
    vector_store = get_vector_store()
    chunker = TextChunker(chunk_size=1000, chunk_overlap=200)
    return DocumentProcessor(embeddings, vector_store, chunker)


@lru_cache()
def get_query_interface() -> BRFQueryInterface:
    logger.info("Initializing BRFQueryInterface")
    processor = get_document_processor()
    return BRFQueryInterface(processor)
