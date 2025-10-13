# BRF Helper 🏢

AI-powered tool for analyzing Swedish BRF (Bostadsrättsförening) annual reports using RAG (Retrieval Augmented Generation).

Ask questions about housing cooperative finances in natural language and get AI-generated answers with source citations.

## Features

- 📄 **PDF Processing** - Extract and chunk BRF annual reports
- 🔍 **Hybrid Search** - Combines semantic search (vector embeddings) with keyword matching (BM25)
- 🤖 **AI-Powered Q&A** - Ask questions in Swedish, get accurate answers
- 💬 **Chat Interface** - Interactive conversations about BRF reports
- 🌐 **REST API** - Full-featured FastAPI backend
- ⚡ **CLI Tool** - Simple command-line interface
- 🖥️ **Web UI** - Interactive Streamlit frontend
- 📊 **Source Citations** - Track where information comes from

## Tech Stack

- **Python 3.13** with `uv` package manager
- **Google Gemini** for embeddings and chat
- **ChromaDB** for vector storage + **BM25** for keyword matching
- **FastAPI** for REST API
- **Streamlit** for web UI
- **Typer** + **Rich** for CLI

## Quick Start

### 1. Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- Google API key (for Gemini)

### 2. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd brf-helper

# Install dependencies
uv sync

# Install package in editable mode
uv pip install -e .

# Set up environment
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### 3. Ingest Sample Data

```bash
# Process sample PDFs and create vector database
brf ingest data/
```

### 4. Start the Web UI

```bash
# Launch Streamlit app
uv run streamlit run app.py
```

Open http://localhost:8501 in your browser

**Or use the CLI:**

```bash
# Ask a question
brf query "Vad är årets resultat?"

# Start interactive chat
brf chat

# Show database info
brf info
```

## Usage

### Web UI (Recommended)

Start the Streamlit app:

```bash
uv run streamlit run app.py
```

The web interface provides:
- **💬 Chat Tab** - Interactive conversation with your BRF reports
- **🔍 Query Tab** - Ask single questions with source citations
- **📤 Upload Tab** - Upload new PDF reports to the database
- **⚙️ Sidebar** - Filter by BRF name, toggle sources, view database stats

### CLI Tool

```bash
# Get help
brf --help

# Ask questions
brf query "Hur ser ekonomin ut?"
brf query "Vad är soliditeten?" --brf "brf_fribergsgatan_8_2024"
brf query "Question" --no-sources  # Hide source citations

# Interactive chat
brf chat

# Ingest documents
brf ingest path/to/report.pdf
brf ingest data/ --reset  # Reset database before ingesting

# Database info
brf info
```

### REST API

Start the API server:

```bash
uv run python run_api.py
```

The API will be available at `http://localhost:8000`

#### API Endpoints

- `GET /health` - Health check
- `POST /query` - Ask questions with source citations
- `POST /chat` - Conversational queries
- `POST /upload` - Upload new PDF documents
- `GET /collection/info` - Database statistics
- `GET /docs` - Interactive API documentation

#### Example API Calls

```bash
# Health check
curl http://localhost:8000/health

# Query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Vad är årets resultat?", "include_sources": true}'

# Chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hur ser soliditeten ut?"}'
```

### Python API

```python
from brf_helper.etl.document_processor import DocumentProcessor
from brf_helper.etl.vector_store import BRFVectorStore
from brf_helper.llm.embeddings import GeminiEmbeddings
from brf_helper.llm.rag_interface import BRFQueryInterface

# Initialize components with hybrid search enabled (default)
embeddings = GeminiEmbeddings()
vector_store = BRFVectorStore(enable_hybrid=True)
vector_store.create_collection("brf_reports")

processor = DocumentProcessor(embeddings, vector_store)
query_interface = BRFQueryInterface(processor, use_hybrid=True)

# Ask a question - uses hybrid retrieval for better results
result = query_interface.query("Vad är årets resultat?")
print(result["answer"])

# Disable hybrid search if needed
query_interface_vector_only = BRFQueryInterface(processor, use_hybrid=False)
```

## Development

### Project Structure

```
brf-helper/
├── brf_helper/
│   ├── api/           # FastAPI application
│   ├── etl/           # PDF processing & vector DB
│   ├── llm/           # Gemini embeddings & chat
│   └── cli.py         # CLI tool
├── tests/             # Test suite
├── app.py             # Streamlit web UI
├── data/              # Sample PDF reports
└── pyproject.toml     # Dependencies
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=brf_helper

# Run specific test file
uv run pytest tests/test_api.py -v
```

### Code Quality

```bash
# Format code (if ruff is installed)
ruff format .

# Lint code
ruff check .
```

## Configuration

### Environment Variables

Create a `.env` file:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

### Search & Retrieval

- **Hybrid Search**: Combines semantic search (ChromaDB) with keyword matching (BM25)
- **Vector Database**: ChromaDB stored in `./chroma_db/` (not checked into git)
- **BM25 Index**: Cached in `./chroma_db/bm25_index.pkl` for fast keyword search
- **Search Weight**: 70% semantic search, 30% keyword matching (configurable)
- **Chunk size**: 1000 characters with 200 character overlap
- **Embedding model**: `text-embedding-004`
- **Chat model**: `gemini-2.0-flash-exp`

## Examples

### Example 1: Query All BRFs

```bash
brf query "Jämför skuldsättningen mellan BRF:erna"
```

### Example 2: Filter by Specific BRF

```bash
brf query "Vad är årets resultat?" --brf "brf_fribergsgatan_8_2024"
```

### Example 3: Interactive Chat

```bash
brf chat
> Vad är soliditeten för Fribergsgatan?
> Hur ser det ut jämfört med förra året?
> Vad betyder det för föreningens ekonomi?
```

### Example 4: Ingest New Documents

```bash
# Single file
brf ingest path/to/new_report.pdf --name "BRF Name"

# Directory
brf ingest data/2024_reports/

# Reset database and reingest
brf ingest data/ --reset
```

## Limitations

- Requires Google Gemini API key (free tier has rate limits)
- Optimized for Swedish BRF annual reports
- Vector database is local (not shared across instances)
- No authentication (API is open)

## Roadmap

- [x] Web frontend (Streamlit)
- [x] Hybrid retrieval (semantic + keyword search)
- [ ] Multi-user support with authentication
- [ ] Automatic BRF report fetching
- [ ] Historical trend analysis
- [ ] Export functionality
- [ ] Docker deployment
- [ ] Configurable search weights in UI

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Powered by [Google Gemini](https://ai.google.dev/)
- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Vector search by [ChromaDB](https://www.trychroma.com/)
- CLI by [Typer](https://typer.tiangolo.com/)
