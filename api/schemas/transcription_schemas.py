from pydantic import BaseModel, Field
from typing import Dict, Any, List

class TranscriptionRequest(BaseModel):
    text: str = Field(..., description="Texte transcrit à insérer dans Pinecone")
    source: str = Field("transcription", description="Source de la transcription")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées additionnelles")
    chunk_size: int = Field(3000, description="Taille approximative de chaque chunk en caractères")
    chunk_overlap: int = Field(200, description="Chevauchement entre les chunks en caractères")

class TranscriptionResponse(BaseModel):
    message: str
    chunk_ids: List[str]
    chunk_count: int