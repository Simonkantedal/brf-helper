import logging
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import tempfile
import shutil

from brf_helper.api.models import (
    QueryRequest,
    QueryResponse,
    ChatMessage,
    ChatResponse,
    UploadResponse,
    CollectionInfo,
    HealthResponse,
    Source
)
from brf_helper.api.dependencies import (
    get_query_interface,
    get_document_processor,
    get_vector_store
)
from brf_helper.llm.rag_interface import BRFQueryInterface
from brf_helper.etl.document_processor import DocumentProcessor
from brf_helper.etl.vector_store import BRFVectorStore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("chromadb").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BRF Helper API",
    description="API for querying Swedish BRF annual reports using AI",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="healthy", version="0.1.0")


@app.post("/query", response_model=QueryResponse)
async def query_brf(
    request: QueryRequest,
    query_interface: BRFQueryInterface = Depends(get_query_interface)
):
    try:
        logger.info(f"Received query: {request.question}")
        
        result = query_interface.query(
            question=request.question,
            brf_name=request.brf_name,
            include_sources=request.include_sources
        )
        
        sources = None
        if request.include_sources and result.get("sources"):
            sources = [Source(**source) for source in result["sources"]]
        
        return QueryResponse(
            question=result["question"],
            answer=result["answer"],
            brf_name=result.get("brf_name"),
            sources=sources
        )
    
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat", response_model=ChatResponse)
async def chat_with_brf(
    message: ChatMessage,
    query_interface: BRFQueryInterface = Depends(get_query_interface)
):
    try:
        logger.info(f"Received chat message: {message.message}")
        
        response = query_interface.chat(
            message=message.message,
            brf_name=message.brf_name
        )
        
        return ChatResponse(
            message=message.message,
            response=response
        )
    
    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    brf_name: str | None = None,
    processor: DocumentProcessor = Depends(get_document_processor)
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        logger.info(f"Uploading PDF: {file.filename}")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
        
        try:
            result = processor.process_pdf(tmp_path, brf_name)
            
            return UploadResponse(**result)
        
        finally:
            Path(tmp_path).unlink()
    
    except Exception as e:
        logger.error(f"Error uploading PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collection/info", response_model=CollectionInfo)
async def get_collection_info(
    vector_store: BRFVectorStore = Depends(get_vector_store)
):
    try:
        info = vector_store.get_collection_info()
        return CollectionInfo(**info)
    
    except Exception as e:
        logger.error(f"Error getting collection info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup_event():
    logger.info("Starting BRF Helper API...")
    logger.info("Initializing dependencies...")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down BRF Helper API...")
