from fastapi import APIRouter, Depends, HTTPException, Query
from api.schemas.transcription_schemas import TranscriptionRequest, TranscriptionResponse
from api.utils.chromadb_utils import upsert_vector 
from api.utils.gemini_utils import EMBEDDING_MODEL_NAME, EMBEDDING_DIMENSION 
from api.middlewares.auth_middleware import get_current_user
from api.utils.text_utils import chunk_text
from typing import Dict, Any
from datetime import datetime
import logging 

logger = logging.getLogger(__name__) 

router = APIRouter(prefix="/transcriptions", tags=["Transcriptions"])

@router.post("/store", response_model=TranscriptionResponse)
async def store_transcription(
    request: TranscriptionRequest,
    auto_embed: bool = Query(True, description="Créer automatiquement les embeddings avec Gemini"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> TranscriptionResponse:
    """
    Stocke un texte transcrit dans ChromaDB pour RAG en le découpant en chunks.
    Associe les chunks à l'utilisateur courant.
    """
    if not request.text or not request.text.strip():
        logger.warning(f"User {current_user.get('id')} attempted to store empty transcription.")
        raise HTTPException(status_code=400, detail="Le texte transcrit est requis")
    
    user_id = str(current_user["id"]) # Assurer string pour ChromaDB metadata
    logger.info(f"User {user_id} storing transcription in ChromaDB (source: {request.source}, auto_embed: {auto_embed}).")
    
    # Préparer les métadonnées de base, incluant l'user_id
    base_metadata = {
        "source": request.source,
        "user_id": user_id, # Ajouté pour le filtrage
        "timestamp": datetime.now().isoformat(),
        "embedding_model": EMBEDDING_MODEL_NAME, 
        "dimension": EMBEDDING_DIMENSION,        
        **(request.metadata or {}) 
    }
    
    try:
        # Découper le texte en chunks
        logger.debug(f"Chunking text for user {user_id}...")
        chunks = await chunk_text(
            text=request.text,
            chunk_size=request.chunk_size,
            overlap=request.chunk_overlap,
            metadata=base_metadata 
        )
        
        if not chunks:
            logger.warning(f"Could not create text chunks for user {user_id}.")
            raise HTTPException(status_code=400, detail="Impossible de créer des chunks à partir du texte fourni.")
        
        logger.info(f"Created {len(chunks)} chunks for user {user_id}.")
        
        # Stocker chaque chunk dans ChromaDB
        chunk_ids = []
        processed_chunks = 0
        for chunk in chunks:
            try:
                # La logique d'embedding est gérée dans upsert_vector de chromadb_utils
                if auto_embed:
                     chunk.embedding = None # Force la création dans upsert_vector
                else:
                     # Si auto_embed est False, on suppose que l'embedding est déjà fourni ou non nécessaire
                     chunk.embedding = None 
                     logger.debug(f"Skipping embedding generation for chunk {chunk.id} (auto_embed=False).")

                # Stocker le vecteur via la fonction upsert_vector de chromadb_utils
                await upsert_vector(chunk) 
                chunk_ids.append(chunk.id)
                processed_chunks += 1
            except ValueError as ve: # Capturer les erreurs spécifiques (ex: dimension)
                 logger.error(f"ValueError processing chunk {chunk.id} for user {user_id} (ChromaDB): {ve}")
                 continue # Continuer avec le chunk suivant
            except RuntimeError as re: # Capturer les erreurs d'upsert ChromaDB
                 logger.error(f"RuntimeError processing chunk {chunk.id} for user {user_id} (ChromaDB): {re}")
                 # Arrêter le processus si une erreur d'écriture survient
                 raise HTTPException(status_code=503, detail=f"Erreur lors du stockage du chunk {chunk.id} dans ChromaDB.") from re
            except Exception as e:
                 logger.exception(f"Unexpected error processing chunk {chunk.id} for user {user_id} (ChromaDB): {e}")
                 continue # Continuer avec le chunk suivant

        logger.info(f"Successfully processed and stored {processed_chunks}/{len(chunks)} chunks in ChromaDB for user {user_id}.")
        
        if processed_chunks == 0 and len(chunks) > 0:
             # Si aucun chunk n'a été traité avec succès mais qu'il y avait des chunks à traiter
             raise HTTPException(status_code=500, detail="Aucun chunk n'a pu être stocké avec succès dans ChromaDB.")

        return TranscriptionResponse(
            message=f"Transcription stockée avec succès dans ChromaDB. {processed_chunks}/{len(chunks)} chunks traités.",
            chunk_ids=chunk_ids,
            chunk_count=processed_chunks
        )

    except HTTPException as http_exc:
        # Remonter les exceptions HTTP déjà formatées
        raise http_exc
    except Exception as e:
        logger.exception(f"Failed to store transcription in ChromaDB for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"An internal server error occurred during transcription storage: {str(e)}")