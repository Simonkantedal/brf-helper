from pathlib import Path
from brf_helper.etl.document_processor import DocumentProcessor
from brf_helper.etl.vector_store import BRFVectorStore
from brf_helper.etl.text_chunker import TextChunker
from brf_helper.llm.embeddings import GeminiEmbeddings


def main():
    print("Initializing components...")
    
    embeddings = GeminiEmbeddings()
    vector_store = BRFVectorStore(persist_directory="./chroma_db")
    vector_store.create_collection("brf_reports", reset=True)
    
    chunker = TextChunker(chunk_size=1000, chunk_overlap=200)
    processor = DocumentProcessor(embeddings, vector_store, chunker)
    
    print("\nProcessing PDFs from data directory...")
    data_dir = Path("data")
    results = processor.process_directory(data_dir)
    
    print("\nIngestion complete!")
    for result in results:
        print(f"\n  BRF: {result['brf_name']}")
        print(f"  Pages: {result['num_pages']}")
        print(f"  Chunks: {result['num_chunks']}")
    
    info = vector_store.get_collection_info()
    print(f"\nTotal documents in collection: {info['count']}")
    
    print("\n\nTesting search...")
    query = "Vad är årets resultat?"
    print(f"Query: '{query}'")
    
    search_results = processor.search(query, n_results=3)
    
    print("\nTop results:")
    for i, (doc, metadata, distance) in enumerate(zip(
        search_results["documents"],
        search_results["metadatas"],
        search_results["distances"]
    ), 1):
        print(f"\n{i}. Distance: {distance:.4f}")
        print(f"   BRF: {metadata.get('brf_name', 'N/A')}")
        print(f"   Page: {metadata.get('page_number', 'N/A')}")
        print(f"   Text: {doc[:200]}...")


if __name__ == "__main__":
    main()
