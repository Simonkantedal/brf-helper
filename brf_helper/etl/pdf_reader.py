from pathlib import Path
from pypdf import PdfReader


class BRFPdfReader:
    def __init__(self, pdf_path: str | Path):
        self.pdf_path = Path(pdf_path)
        self.reader = PdfReader(str(self.pdf_path))
        self.num_pages = len(self.reader.pages)
    
    def extract_text(self, page_num: int | None = None) -> str:
        if page_num is not None:
            if 0 <= page_num < self.num_pages:
                return self.reader.pages[page_num].extract_text()
            raise ValueError(f"Page {page_num} out of range (0-{self.num_pages-1})")
        
        return "\n\n".join(
            page.extract_text() for page in self.reader.pages
        )
    
    def extract_all_pages(self) -> list[dict[str, any]]:
        pages = []
        for i, page in enumerate(self.reader.pages):
            pages.append({
                "page_number": i + 1,
                "text": page.extract_text(),
                "char_count": len(page.extract_text())
            })
        return pages
    
    def get_metadata(self) -> dict[str, any]:
        return {
            "file_path": str(self.pdf_path),
            "file_name": self.pdf_path.name,
            "num_pages": self.num_pages,
            "metadata": self.reader.metadata
        }
