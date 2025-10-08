import re


class TextChunker:
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separator: str = "\n\n"
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator
    
    def chunk_text(self, text: str, metadata: dict = None) -> list[dict[str, any]]:
        paragraphs = text.split(self.separator)
        
        chunks = []
        current_chunk = ""
        chunk_index = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            if len(current_chunk) + len(paragraph) + len(self.separator) <= self.chunk_size:
                current_chunk += paragraph + self.separator
            else:
                if current_chunk:
                    chunks.append(self._create_chunk(current_chunk, chunk_index, metadata))
                    chunk_index += 1
                    
                    overlap_text = self._get_overlap_text(current_chunk)
                    current_chunk = overlap_text + paragraph + self.separator
                else:
                    current_chunk = paragraph + self.separator
        
        if current_chunk:
            chunks.append(self._create_chunk(current_chunk, chunk_index, metadata))
        
        return chunks
    
    def _create_chunk(self, text: str, index: int, metadata: dict = None) -> dict[str, any]:
        chunk = {
            "chunk_index": index,
            "text": text.strip(),
            "char_count": len(text.strip())
        }
        
        if metadata:
            chunk["metadata"] = metadata
        
        return chunk
    
    def _get_overlap_text(self, text: str) -> str:
        if len(text) <= self.chunk_overlap:
            return text
        
        return text[-self.chunk_overlap:]
    
    def chunk_pages(self, pages: list[dict[str, any]]) -> list[dict[str, any]]:
        all_chunks = []
        
        for page in pages:
            page_metadata = {
                "page_number": page.get("page_number"),
                "source": page.get("source")
            }
            
            page_chunks = self.chunk_text(page["text"], page_metadata)
            all_chunks.extend(page_chunks)
        
        return all_chunks
