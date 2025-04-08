from typing import List, Dict, Any
import uuid
import re
from api.schemas.content_schemas import ContentChunk
from api.utils.gemini_utils import EMBEDDING_MODEL_NAME, EMBEDDING_DIMENSION

async def chunk_text(text: str, chunk_size: int = 3000, overlap: int = 200, 
                     metadata: Dict[str, Any] = None) -> List[ContentChunk]:
    """
    Découpe un texte long en chunks avec chevauchement pour améliorer la recherche RAG.
    
    Args:
        text: Texte à découper
        chunk_size: Taille approximative de chaque chunk en caractères
        overlap: Chevauchement entre les chunks en caractères
        metadata: Métadonnées communes à tous les chunks (ex: user_id, source_id)
    
    Returns:
        Liste de ContentChunk prêts à être insérés dans Pinecone
    """
    if not text:
        return []
    
    # Métadonnées par défaut ou fournies
    base_metadata = metadata or {}
    
    # Diviser le texte en paragraphes ou sections logiques si possible
    # Utiliser une regex plus robuste pour séparer les blocs de texte
    paragraphs = re.split(r'(\n\s*\n+)', text) # Garde les séparateurs pour reconstruire si besoin
    
    # Filtrer les éléments vides et recombiner les paragraphes avec leurs séparateurs
    processed_paragraphs = []
    temp_para = ""
    for item in paragraphs:
        if item.strip(): # Si ce n'est pas juste un espace blanc/nouvelle ligne
            temp_para += item
        elif temp_para: # Si on rencontre un séparateur et qu'on a du texte accumulé
             processed_paragraphs.append(temp_para.strip())
             temp_para = ""
    if temp_para: # Ajouter le dernier paragraphe s'il existe
        processed_paragraphs.append(temp_para.strip())

    if not processed_paragraphs: # Si le découpage initial ne donne rien, utiliser le texte entier
        processed_paragraphs = [text.strip()]

    chunks = []
    current_chunk_text = ""
    chunk_index = 0
    total_paragraphs = len(processed_paragraphs) # Nombre total de paragraphes/blocs
    
    for i, para in enumerate(processed_paragraphs):
        para_len = len(para)
        current_chunk_len = len(current_chunk_text)

        # Si l'ajout du paragraphe dépasse la taille max du chunk
        # (ajouter 2 pour l'espace potentiel ou \n\n)
        if current_chunk_len > 0 and current_chunk_len + para_len + 2 > chunk_size:
            # Finaliser le chunk actuel
            chunk_id = f"chunk-{str(uuid.uuid4())}"
            chunk_metadata = {
                **base_metadata,
                "chunk_index": chunk_index,
                "position": f"{chunk_index + 1}/{total_paragraphs}", # Position basée sur les paragraphes
                "embedding_model": EMBEDDING_MODEL_NAME, # Utiliser la constante
                "dimension": EMBEDDING_DIMENSION, # Utiliser la constante
                # Ajouter d'autres métadonnées si pertinent
            }
            chunks.append(ContentChunk(
                id=chunk_id,
                text=current_chunk_text.strip(),
                metadata=chunk_metadata
            ))
            chunk_index += 1
            
            # Commencer un nouveau chunk avec chevauchement
            overlap_text = current_chunk_text[-overlap:].lstrip() if overlap > 0 else ""
            current_chunk_text = overlap_text + "\n\n" + para if overlap_text else para # Ajouter le paragraphe actuel au nouveau chunk
        
        # Sinon, ajouter le paragraphe au chunk actuel
        else:
            if current_chunk_text:
                current_chunk_text += "\n\n" + para
            else:
                current_chunk_text = para

    # Ajouter le dernier chunk s'il contient du texte
    if current_chunk_text.strip():
        chunk_id = f"chunk-{str(uuid.uuid4())}"
        chunk_metadata = {
            **base_metadata,
            "chunk_index": chunk_index,
            "position": f"{chunk_index + 1}/{total_paragraphs}",
            "embedding_model": EMBEDDING_MODEL_NAME, # Utiliser la constante
            "dimension": EMBEDDING_DIMENSION, # Utiliser la constante
        }
        chunks.append(ContentChunk(
            id=chunk_id,
            text=current_chunk_text.strip(),
            metadata=chunk_metadata
        ))

    return chunks