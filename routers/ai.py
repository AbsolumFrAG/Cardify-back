from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List, Optional
from models.flashcard import FlashcardBatch, Language
from models.flashcard import GenerateFlashcardsRequest
from services.flashcard_service import create_flashcards_batch
from services.gemini_service import generate_flashcards
import base64
from middlewares.authentication import get_current_user

router = APIRouter()

@router.post("/generate-from-images", response_model=FlashcardBatch)
async def generate_from_images(
    files: List[UploadFile] = File(...),
    count: int = Form(...),
    language: Language = Form(Language.FRENCH),
    course_name: Optional[str] = Form(None),
    tags: List[str] = Form([]),
    user = Depends(get_current_user)
):
    """Générer des flashcards à partir d'images téléchargées en utilisant l'API Gemini."""
    if count <= 0 or count > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le nombre doit être compris entre 1 et 50"
        )
    
    try:
        # Conversion des fichiers téléchargés en base64
        image_data_list = []
        for file in files:
            contents = await file.read()
            base64_image = base64.b64encode(contents).decode("utf-8")
            image_data_list.append(base64_image)
        
        # Génération de flashcards avec l'API Gemini
        generated_flashcards = await generate_flashcards(
            image_data_list=image_data_list,
            count=count,
            language=language,
            course_name=course_name,
            tags=tags
        )
        
        # Sauvegarde des flashcards générées dans la base de données
        created_cards = await create_flashcards_batch(generated_flashcards, user.id)
        
        return FlashcardBatch(flashcards=created_cards, count=len(created_cards))
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Une erreur est survenue: {str(e)}"
        )

@router.post("/generate-from-base64", response_model=FlashcardBatch)
async def generate_from_base64(
    request_data: GenerateFlashcardsRequest,
    user = Depends(get_current_user)
):
    """Générer des flashcards à partir d'images encodées en base64 en utilisant l'API Gemini."""
    if request_data.count <= 0 or request_data.count > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le nombre doit être compris entre 1 et 50"
        )
    
    try:
        # Génération de flashcards avec l'API Gemini
        generated_flashcards = await generate_flashcards(
            image_data_list=request_data.image_data,
            count=request_data.count,
            language=request_data.language,
            course_name=request_data.course_name,
            tags=request_data.tags
        )
        
        # Sauvegarde des flashcards générées dans la base de données
        created_cards = await create_flashcards_batch(generated_flashcards, user.id)
        
        return FlashcardBatch(flashcards=created_cards, count=len(created_cards))
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Une erreur est survenue: {str(e)}"
        )