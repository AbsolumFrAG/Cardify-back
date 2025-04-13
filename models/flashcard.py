from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class Language(str, Enum):
    FRENCH = "fr"
    ENGLISH = "en"
    SPANISH = "es"
    GERMAN = "de"
    ITALIAN = "it"
    VIETNAMESE = "vi"
    THAI = "th"

class FlashcardCreate(BaseModel):
    question: str
    answer: str
    course_name: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

class FlashcardResponse(BaseModel):
    id: str
    user_id: str
    question: str
    answer: str
    course_name: Optional[str] = None
    tags: List[str] = []
    created_at: datetime

class FlashcardBatch(BaseModel):
    flashcards: List[FlashcardResponse]
    count: int

class GenerateFlashcardsRequest(BaseModel):
    image_data: List[str]
    count: int = Field(..., gt=0, le=50, description="Nombre de flashcards à générer (max 50)")
    language: Language = Language.FRENCH
    course_name: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

class UserSignUp(BaseModel):
    email: str
    password: str = Field(..., min_length=8)

class UserSignIn(BaseModel):
    email: str
    password: str

class GoogleSignIn(BaseModel):
    token: str