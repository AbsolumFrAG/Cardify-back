from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from models.flashcard import FlashcardResponse, FlashcardCreate, FlashcardBatch
from services.flashcard_service import (
    create_flashcard, 
    create_flashcards_batch, 
    get_user_flashcards, 
    delete_flashcard
)
from middlewares.authentication import get_current_user

router = APIRouter()

@router.post("/", response_model=FlashcardResponse)
async def create_new_flashcard(
    flashcard: FlashcardCreate, 
    user = Depends(get_current_user)
):
    """Créer une nouvelle flashcard pour l'utilisateur authentifié."""
    try:
        result = await create_flashcard(flashcard, user.id)
        return result
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

@router.post("/batch", response_model=FlashcardBatch)
async def create_flashcards_in_batch(
    flashcards: List[FlashcardCreate],
    user = Depends(get_current_user)
):
    """Créer plusieurs flashcards en une seule requête."""
    try:
        created_cards = await create_flashcards_batch(flashcards, user.id)
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

@router.get("/", response_model=List[FlashcardResponse])
async def get_flashcards(
    limit: int = 100,
    offset: int = 0,
    course_name: Optional[str] = None,
    tags: Optional[List[str]] = None,
    user = Depends(get_current_user)
):
    """Récupérer les flashcards de l'utilisateur authentifié avec filtrage optionnel."""
    try:
        flashcards = await get_user_flashcards(
            user.id, 
            limit=limit, 
            offset=offset,
            course_name=course_name,
            tags=tags
        )
        return flashcards
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Une erreur est survenue: {str(e)}"
        )

@router.delete("/{flashcard_id}")
async def remove_flashcard(
    flashcard_id: str,
    user = Depends(get_current_user)
):
    """Supprimer une flashcard par ID si elle appartient à l'utilisateur authentifié."""
    try:
        await delete_flashcard(flashcard_id, user.id)
        return {"message": "Flashcard supprimée avec succès"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Une erreur est survenue: {str(e)}"
        )