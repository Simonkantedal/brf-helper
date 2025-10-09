from pathlib import Path
from typing import List, Dict
from brf_helper.etl.pdf_reader import BRFPdfReader
from brf_helper.etl.text_chunker import TextChunker
from brf_helper.etl.vector_store import BRFVectorStore
from brf_helper.llm.embeddings import GeminiEmbeddings


class DocumentProcessor:
    def __init__(
        self,
        embeddings: GeminiEmbeddings,
        vector_store: BRFVectorStore,
        chunker: TextChunker = None
    ):
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.chunker = chunker or TextChunker()
    
    def process_pdf(self, pdf_path: str | Path, brf_name: str = None) -> Dict:
        pdf_path = Path(pdf_path)
        if brf_name is None:
            brf_name = pdf_path.stem
        
        reader = BRFPdfReader(pdf_path)
        pages = reader.extract_all_pages()
        
        for page in pages:
            page["source"] = str(pdf_path)
            page["brf_name"] = brf_name
        
        chunks = self.chunker.chunk_pages(pages)
        
        texts = [chunk["text"] for chunk in chunks]
        embeddings_list = self.embeddings.embed_batch(texts)
        
        metadatas = []
        ids = []
        for i, chunk in enumerate(chunks):
            metadata = {
                "brf_name": brf_name,
                "source": str(pdf_path),
                "chunk_index": chunk["chunk_index"],
                "char_count": chunk["char_count"]
            }
            if "metadata" in chunk and chunk["metadata"]:
                metadata.update(chunk["metadata"])
            
            metadatas.append(metadata)
            ids.append(f"{brf_name}_{i}")
        
        self.vector_store.add_documents(
            texts=texts,
            embeddings=embeddings_list,
            metadatas=metadatas,
            ids=ids
        )
        
        return {
            "brf_name": brf_name,
            "source": str(pdf_path),
            "num_pages": len(pages),
            "num_chunks": len(chunks),
            "processed": True
        }
    
    def process_directory(self, directory: str | Path, pattern: str = "*.pdf") -> List[Dict]:
        directory = Path(directory)
        pdf_files = list(directory.glob(pattern))
        
        results = []
        for pdf_file in pdf_files:
            result = self.process_pdf(pdf_file)
            results.append(result)
        
        return results
    
    def search(self, query: str, n_results: int = 5, brf_name: str = None) -> Dict:
        query_embedding = self.embeddings.embed_query(query)
        
        where = {"brf_name": brf_name} if brf_name else None
        
        results = self.vector_store.search(
            query_embedding=query_embedding,
            n_results=n_results,
            where=where
        )
        
        return results
