from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class ImageToTextRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded image data")

class ImageToTextResponse(BaseModel):
    text: str
    success: bool = True
    error_message: Optional[str] = None
    confidence: Optional[float] = None

class FlashcardRequest(BaseModel):
    text: str = Field(..., description="Text content to generate flashcards from")
    num_cards: int = Field(5, description="Number of flashcards to generate")

class Flashcard(BaseModel):
    question: str
    answer: str

class FlashcardResponse(BaseModel):
    flashcards: List[Flashcard]

class ContentChunk(BaseModel):
    id: str
    text: str
    metadata: Dict[str, Any] = {}
    embedding: Optional[List[float]] = None
    score: Optional[float] = None

class QueryRequest(BaseModel):
    query_text: str
    top_k: int = 5

class RAGRequest(BaseModel):
    question: str

class RAGResponse(BaseModel):
    answer: str