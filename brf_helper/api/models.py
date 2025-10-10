from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., description="Question about BRF reports")
    brf_name: str | None = Field(None, description="Filter by specific BRF name")
    include_sources: bool = Field(True, description="Include source citations")


class Source(BaseModel):
    brf_name: str
    page_number: int | None
    relevance_score: float


class QueryResponse(BaseModel):
    question: str
    answer: str
    brf_name: str | None
    sources: list[Source] | None = None


class ChatMessage(BaseModel):
    message: str = Field(..., description="Chat message")
    brf_name: str | None = Field(None, description="Filter by specific BRF name")


class ChatResponse(BaseModel):
    message: str
    response: str


class UploadResponse(BaseModel):
    brf_name: str
    source: str
    num_pages: int
    num_chunks: int
    processed: bool


class CollectionInfo(BaseModel):
    name: str
    count: int


class HealthResponse(BaseModel):
    status: str
    version: str
