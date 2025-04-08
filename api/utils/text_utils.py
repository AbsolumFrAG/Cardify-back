from fastapi import APIRouter, Depends, HTTPException
from api.schemas.content_schemas import (
    ImageToTextRequest,
    ImageToTextResponse,
    FlashcardRequest,
    FlashcardResponse,
)
from api.utils.gemini_utils import extract_text_from_image, generate_flashcards 
from api.middlewares.auth_middleware import get_current_user
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# Renommer le préfixe et les tags
router = APIRouter(prefix="/ai", tags=["AI Services (Gemini)"]) 

@router.post("/extract-text", response_model=ImageToTextResponse)
async def extract_text(
    request: ImageToTextRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> ImageToTextResponse:
    """Extract text from an image using Gemini Vision"""
    if not request.image_base64:
        logger.warning(f"User {current_user.get('id')} requested text extraction without image data.")
        raise HTTPException(status_code=400, detail="Image data (base64 encoded) is required")
    
    logger.info(f"User {current_user.get('id')} requesting text extraction from image.")
    # Appeler la fonction de gemini_utils
    result = await extract_text_from_image(request.image_base64) 
    
    if not result["success"]:
         logger.error(f"Text extraction failed for user {current_user.get('id')}: {result.get('error_message')}")
         # Retourner une réponse d'erreur claire mais sans exposer trop de détails internes
         raise HTTPException(status_code=500, detail=result.get("error_message", "Text extraction failed"))

    logger.info(f"Text extraction successful for user {current_user.get('id')}.")
    return ImageToTextResponse(**result)

@router.post("/generate-flashcards", response_model=FlashcardResponse)
async def create_flashcards(
    request: FlashcardRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> FlashcardResponse:
    """Generate flashcards from text using Gemini"""
    if not request.text or not request.text.strip():
        logger.warning(f"User {current_user.get('id')} requested flashcard generation with empty text.")
        raise HTTPException(status_code=400, detail="Text content is required")
    
    if request.num_cards <= 0:
        logger.warning(f"User {current_user.get('id')} requested non-positive number of flashcards: {request.num_cards}")
        raise HTTPException(status_code=400, detail="Number of cards must be greater than 0")
    
    logger.info(f"User {current_user.get('id')} requesting {request.num_cards} flashcards.")
    # Appeler la fonction de gemini_utils
    flashcards_data = await generate_flashcards(request.text, request.num_cards) 
    
    if not flashcards_data:
        logger.warning(f"Flashcard generation returned no results for user {current_user.get('id')}.")
        # Peut-être que le texte était trop court ou inapproprié
        raise HTTPException(status_code=404, detail="Could not generate flashcards from the provided text. The text might be too short or lack sufficient information.")

    # Pas besoin de convertir ici si gemini_utils retourne déjà le bon format
    # flashcards = [Flashcard(**card) for card in flashcards_data] 
    logger.info(f"Flashcard generation successful for user {current_user.get('id')}, generated {len(flashcards_data)} cards.")
    return FlashcardResponse(flashcards=flashcards_data)