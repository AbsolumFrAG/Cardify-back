from typing import List, Optional
from models.flashcard import FlashcardCreate, FlashcardResponse
from config import get_settings
from supabase import create_client

settings = get_settings()

def get_supabase_client():
    return create_client(settings.supabase_url, settings.supabase_key)

async def create_flashcard(flashcard: FlashcardCreate, user_id: str) -> FlashcardResponse:
    """Créer une nouvelle flashcard dans la base de données."""
    supabase = get_supabase_client()

    data = {
        "user_id": user_id,
        "question": flashcard.question,
        "answer": flashcard.answer,
        "course_name": flashcard.course_name,
        "tags": flashcard.tags,
    }

    result = supabase.table("flashcards").insert(data).execute()

    if len(result.data) == 0:
        raise ValueError("Échec de création de la flashcard")
    
    created_card = result.data[0]
    return FlashcardResponse(**created_card)

async def create_flashcards_batch(
        flashcards: List[FlashcardCreate],
        user_id: str
) -> List[FlashcardResponse]:
    """Créer plusieurs flashcards en une seule opération."""
    supabase = get_supabase_client()

    data = []
    for flashcard in flashcards:
        data.append({
            "user_id": user_id,
            "question": flashcard.question,
            "answer": flashcard.answer,
            "course_name": flashcard.course_name,
            "tags": flashcard.tags,
        })

    result = supabase.table("flashcards").insert(data).execute()

    if len(result.data) == 0:
        raise ValueError("Échec de création des flashcards")
    
    created_cards = [FlashcardResponse(**card) for card in result.data]
    return created_cards

async def get_user_flashcards(
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        course_name: Optional[str] = None,
        tags: Optional[List[str]] = None
) -> List[FlashcardResponse]:
    """Récupérer les flashcards d'un utilisateur avec filtrage optionnel."""
    supabase = get_supabase_client()

    query = supabase.table("flashcards").select("*").eq("user_id", user_id)

    # Application des filtres si fournis
    if course_name:
        query = query.eq("course_name", course_name)

    if tags and len(tags) > 0:
        query = query.contains("tags", tags)

    # Application de la pagination
    query = query.range(offset, offset + limit - 1).order("created_at", desc=True)

    result = query.execute()

    return [FlashcardResponse(**card) for card in result.data]

async def delete_flashcard(flashcard_id: str, user_id: str) -> bool:
    """Supprimer une flashcard par ID, en s'assurant qu'elle appartient à l'utilisateur spécifié."""
    supabase = get_supabase_client()

    # Vérification que la flashcard appartient à l'utilisateur
    result = supabase.table("flashcards").select("*").eq("id", flashcard_id).eq("user_id", user_id).execute()

    if len(result.data) == 0:
        raise ValueError("Flashcard non trouvée ou n'appartient pas à l'utilisateur")
    
    # Si la flashcard existe et appartient à l'utilisateur, la supprimer
    delete_result = supabase.table("flashcards").delete().eq("id", flashcard_id).execute()

    return True