import pytest
from pathlib import Path
from brf_helper.etl.pdf_reader import BRFPdfReader
from brf_helper.etl.text_chunker import TextChunker


@pytest.fixture
def sample_pdf_path():
    return Path("data/brf_fribergsgatan_8_2024.pdf")


@pytest.fixture
def pdf_reader(sample_pdf_path):
    return BRFPdfReader(sample_pdf_path)


class TestBRFPdfReader:
    def test_pdf_reader_initialization(self, pdf_reader, sample_pdf_path):
        assert pdf_reader.pdf_path == sample_pdf_path
        assert pdf_reader.num_pages > 0
    
    def test_get_metadata(self, pdf_reader):
        metadata = pdf_reader.get_metadata()
        
        assert "file_path" in metadata
        assert "file_name" in metadata
        assert "num_pages" in metadata
        assert metadata["num_pages"] > 0
        assert metadata["file_name"] == "brf_fribergsgatan_8_2024.pdf"
    
    def test_extract_all_pages(self, pdf_reader):
        pages = pdf_reader.extract_all_pages()
        
        assert len(pages) > 0
        assert all("page_number" in page for page in pages)
        assert all("text" in page for page in pages)
        assert all("char_count" in page for page in pages)
        assert pages[0]["page_number"] == 1
    
    def test_extract_single_page(self, pdf_reader):
        text = pdf_reader.extract_text(page_num=0)
        
        assert isinstance(text, str)
        assert len(text) > 0
    
    def test_extract_all_text(self, pdf_reader):
        text = pdf_reader.extract_text()
        
        assert isinstance(text, str)
        assert len(text) > 0
    
    def test_invalid_page_number(self, pdf_reader):
        with pytest.raises(ValueError):
            pdf_reader.extract_text(page_num=9999)


class TestTextChunker:
    def test_chunker_initialization(self):
        chunker = TextChunker(chunk_size=1000, chunk_overlap=200)
        
        assert chunker.chunk_size == 1000
        assert chunker.chunk_overlap == 200
    
    def test_chunk_text(self):
        chunker = TextChunker(chunk_size=100, chunk_overlap=20)
        text = "This is a test.\n\nThis is another paragraph.\n\nAnd another one."
        
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 0
        assert all("chunk_index" in chunk for chunk in chunks)
        assert all("text" in chunk for chunk in chunks)
        assert all("char_count" in chunk for chunk in chunks)
    
    def test_chunk_pages(self, pdf_reader):
        chunker = TextChunker(chunk_size=1000, chunk_overlap=200)
        pages = pdf_reader.extract_all_pages()
        
        chunks = chunker.chunk_pages(pages)
        
        assert len(chunks) > 0
        assert all("chunk_index" in chunk for chunk in chunks)
        assert all("text" in chunk for chunk in chunks)
        assert all("metadata" in chunk for chunk in chunks)
        assert all("page_number" in chunk["metadata"] for chunk in chunks)
    
    def test_chunk_overlap(self):
        chunker = TextChunker(chunk_size=50, chunk_overlap=10)
        text = "First paragraph.\n\nSecond paragraph that is long enough.\n\nThird paragraph here."
        
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) >= 1
        assert all(len(chunk["text"]) <= chunker.chunk_size + 50 for chunk in chunks)
