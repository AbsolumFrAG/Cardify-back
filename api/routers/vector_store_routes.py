from fastapi import APIRouter, Depends, HTTPException
from api.schemas.content_schemas import (
    ContentChunk,
    QueryRequest,
    RAGRequest,
    RAGResponse
)
from api.utils.chromadb_utils import upsert_vector, query_vectors 
from api.utils.gemini_utils import generate_answer_with_rag
from api.middlewares.auth_middleware import get_current_user
from typing import Dict, Any, List
import logging 

logger = logging.getLogger(__name__) 

# Renommer le préfixe et les tags pour être plus génériques ou spécifiques à ChromaDB
router = APIRouter(prefix="/vector-store", tags=["Vector Store (ChromaDB)"]) 

@router.post("/upsert", status_code=201)
async def create_vector(
    chunk: ContentChunk,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, str]:
    """Add or update a vector in ChromaDB (associating with the current user)"""
    if not chunk.id:
        logger.warning(f"User {current_user.get('id')} attempted upsert without vector ID.")
        raise HTTPException(status_code=400, detail="Vector ID is required")
    
    if not chunk.text or not chunk.text.strip():
        logger.warning(f"User {current_user.get('id')} attempted upsert with empty text for ID {chunk.id}.")
        raise HTTPException(status_code=400, detail="Text content is required")
    
    # Ajouter l'ID de l'utilisateur aux métadonnées pour le filtrage
    chunk.metadata = chunk.metadata or {}
    # Assurer que user_id est bien une string simple pour ChromaDB
    chunk.metadata["user_id"] = str(current_user["id"]) 
    
    try:
        logger.info(f"User {current_user.get('id')} upserting vector ID: {chunk.id} to ChromaDB")
        await upsert_vector(chunk) # Appel de la fonction ChromaDB
        logger.info(f"Vector upsert successful for ID: {chunk.id} by user {current_user.get('id')} in ChromaDB")
        return {"message": "Vector upserted successfully to ChromaDB"}
    except ValueError as ve: 
         logger.error(f"ValueError during ChromaDB upsert for user {current_user.get('id')}, ID {chunk.id}: {ve}")
         raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re: 
         logger.error(f"RuntimeError during ChromaDB upsert for user {current_user.get('id')}, ID {chunk.id}: {re}")
         raise HTTPException(status_code=500, detail="Failed to upsert vector due to a server error with ChromaDB.")
    except Exception as e: 
         logger.exception(f"Unexpected error during ChromaDB upsert for user {current_user.get('id')}, ID {chunk.id}: {e}")
         raise HTTPException(status_code=500, detail="An unexpected error occurred during vector upsert.")


@router.post("/query", response_model=List[ContentChunk])
async def search_vectors(
    request: QueryRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[ContentChunk]:
    """Query similar vectors from ChromaDB (filtered by the current user)"""
    if not request.query_text or not request.query_text.strip():
        logger.warning(f"User {current_user.get('id')} attempted ChromaDB query with empty text.")
        raise HTTPException(status_code=400, detail="Query text is required")
    
    if request.top_k <= 0:
        logger.warning(f"User {current_user.get('id')} requested non-positive top_k for ChromaDB query: {request.top_k}")
        raise HTTPException(status_code=400, detail="Top K must be greater than 0")
    
    try:
        user_id = str(current_user["id"]) # Assurer que c'est une string
        logger.info(f"User {user_id} querying ChromaDB with top_k={request.top_k}: '{request.query_text[:50]}...'")
        # Passer l'user_id pour filtrer les résultats
        results = await query_vectors(request.query_text, request.top_k, user_id=user_id) # Appel de la fonction ChromaDB
        logger.info(f"ChromaDB query successful for user {user_id}, returned {len(results)} results.")
        return results
    except Exception as e:
        logger.exception(f"Error during ChromaDB query for user {current_user.get('id')}: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while querying vectors from ChromaDB.")


@router.post("/rag", response_model=RAGResponse)
async def answer_with_rag(
    request: RAGRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> RAGResponse:
    """Generate an answer using RAG (Retrieval-Augmented Generation) based on user's documents stored in ChromaDB"""
    if not request.question or not request.question.strip():
        logger.warning(f"User {current_user.get('id')} attempted RAG with empty question.")
        raise HTTPException(status_code=400, detail="Question is required")
    
    try:
        user_id = str(current_user["id"]) # Assurer que c'est une string
        logger.info(f"User {user_id} asking RAG question (using ChromaDB context): '{request.question[:50]}...'")
        
        # 1. Récupérer les chunks pertinents pour cet utilisateur depuis ChromaDB
        logger.debug(f"Retrieving relevant context from ChromaDB for user {user_id}...")
        # Utiliser la fonction query_vectors de chromadb_utils
        relevant_chunks = await query_vectors(request.question, top_k=3, user_id=user_id) # Ajuster top_k si nécessaire
        
        if not relevant_chunks:
            logger.warning(f"No relevant context found in ChromaDB for user {user_id} for question: '{request.question[:50]}...'")
            return RAGResponse(answer="Désolé, je n'ai trouvé aucune information pertinente dans vos notes stockées pour répondre à cette question.")
            
        # Construire le contexte pour Gemini
        context = "\n\n---\n\n".join([chunk.text for chunk in relevant_chunks])
        logger.debug(f"Context retrieved from ChromaDB for user {user_id}. Generating RAG answer with Gemini...")

        # 2. Générer la réponse avec Gemini en utilisant le contexte récupéré
        # Utiliser la fonction generate_answer_with_rag de gemini_utils (inchangée)
        answer = await generate_answer_with_rag(request.question, context) 
        logger.info(f"RAG answer generated successfully for user {user_id} using ChromaDB context.")
        
        return RAGResponse(answer=answer)
    except Exception as e:
        logger.exception(f"Error during RAG process (ChromaDB context) for user {current_user.get('id')}: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while generating the answer using retrieved context.")