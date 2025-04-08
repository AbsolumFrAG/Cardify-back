from pinecone import Pinecone, Index
from typing import List
from api.config.settings import get_settings
from api.utils.gemini_utils import create_embedding, EMBEDDING_DIMENSION 
from api.schemas.content_schemas import ContentChunk
import logging

logger = logging.getLogger(__name__)

settings = get_settings()

# Initialisation de Pinecone
try:
    pc = Pinecone(api_key=settings.pinecone_api_key)
    # Note: 'environment' est déprécié. Utilisez l'hôte directement si possible.
    # Si votre index utilise encore 'environment', gardez-le temporairement.
    # host = pc.describe_index(settings.pinecone_index).host # Méthode recommandée
    # index: Index = pc.Index(host=host)
    
    # Méthode alternative si vous utilisez encore l'environnement
    # Vérifiez que l'index existe
    if settings.pinecone_index not in pc.list_indexes().names:
         raise ValueError(f"L'index Pinecone '{settings.pinecone_index}' n'existe pas dans l'environnement/projet spécifié.")
    index: Index = pc.Index(settings.pinecone_index) 
    
    # Vérifier la dimension de l'index (optionnel mais recommandé)
    index_stats = index.describe_index_stats()
    if index_stats.dimension != EMBEDDING_DIMENSION:
        logger.warning(f"Attention: La dimension de l'index Pinecone ({index_stats.dimension}) "
                       f"ne correspond pas à la dimension des embeddings Gemini ({EMBEDDING_DIMENSION}). "
                       f"Cela peut causer des erreurs ou des résultats inattendus.")

except Exception as e:
    logger.error(f"Erreur lors de l'initialisation de Pinecone : {e}", exc_info=True)
    # Gérer l'erreur de manière appropriée, peut-être en levant une exception
    # pour arrêter le démarrage de l'application si Pinecone est essentiel.
    raise RuntimeError(f"Impossible d'initialiser la connexion à Pinecone : {e}") from e


async def upsert_vector(chunk: ContentChunk) -> None:
    """Add or update a vector in Pinecone using the official client"""
    try:
        # S'assurer que l'embedding existe ou le créer
        if not chunk.embedding:
            logger.debug(f"Génération de l'embedding pour le chunk ID: {chunk.id} (tâche: RETRIEVAL_DOCUMENT)")
            # Utiliser le bon task_type pour les documents stockés
            chunk.embedding = await create_embedding(chunk.text, task_type="RETRIEVAL_DOCUMENT") 

        # Vérifier la dimension de l'embedding généré
        if len(chunk.embedding) != EMBEDDING_DIMENSION:
             logger.error(f"Dimension d'embedding incorrecte pour chunk {chunk.id}. Attendu: {EMBEDDING_DIMENSION}, Obtenu: {len(chunk.embedding)}")
             # Lever une exception ou gérer l'erreur comme approprié
             raise ValueError(f"Dimension d'embedding incorrecte générée pour le chunk {chunk.id}.")

        # Préparer les métadonnées
        # Assurez-vous que toutes les valeurs de métadonnées sont des types supportés par Pinecone
        # (string, number, boolean, or list of strings)
        metadata_to_upsert = {
            "text": chunk.text,
            # Convertir les valeurs non supportées si nécessaire
            **{k: str(v) if v is not None else "" for k, v in chunk.metadata.items()} 
        }

        logger.debug(f"Upserting vector ID: {chunk.id} into Pinecone index: {settings.pinecone_index}")
        index.upsert(
            vectors=[(chunk.id, chunk.embedding, metadata_to_upsert)],
            # namespace="votre_namespace" # Décommentez et spécifiez si vous utilisez des namespaces
        )
        logger.info(f"Vector upserted successfully for ID: {chunk.id}")

    except ValueError as ve: # Capturer l'erreur de dimension
        logger.error(f"Erreur de valeur lors de l'upsert Pinecone pour ID {chunk.id}: {ve}", exc_info=True)
        raise ve # Remonter l'erreur pour informer l'appelant
    except Exception as e:
        logger.error(f"Error upserting vector ID {chunk.id} to Pinecone: {e}", exc_info=True)
        # Ne pas remonter l'exception ici pourrait masquer des problèmes
        raise RuntimeError(f"Erreur lors de l'upsert Pinecone pour ID {chunk.id}: {e}") from e

async def query_vectors(query_text: str, top_k: int = 5, user_id: str | None = None) -> List[ContentChunk]:
    """
    Query similar vectors from Pinecone using the official client.
    Optionally filters by user_id if provided in metadata.
    """
    try:
        logger.debug(f"Génération de l'embedding pour la requête (tâche: RETRIEVAL_QUERY): '{query_text[:50]}...'")
        # Utiliser le bon task_type pour les requêtes
        embedding = await create_embedding(query_text, task_type="RETRIEVAL_QUERY")

        # Préparer le filtre si user_id est fourni
        query_filter = None
        if user_id:
            query_filter = {"user_id": {"$eq": user_id}}
            logger.debug(f"Applying filter for user_id: {user_id}")
        
        logger.debug(f"Querying Pinecone index '{settings.pinecone_index}' with top_k={top_k}")
        query_response = index.query(
            vector=embedding,
            top_k=top_k,
            include_metadata=True,
            filter=query_filter, # Ajouter le filtre ici
            # namespace="votre_namespace" # Décommentez si nécessaire
        )

        results = []
        if query_response.matches:
            for match in query_response.matches:
                # Reconstruire les métadonnées originales à partir de metadata_to_upsert
                metadata = match.metadata or {}
                original_metadata = {k: v for k, v in metadata.items() if k != "text"} # Exclure le texte dupliqué
                
                results.append(
                    ContentChunk(
                        id=match.id,
                        text=metadata.get("text", ""), # Récupérer le texte depuis les métadonnées
                        metadata=original_metadata,
                        score=match.score,
                        # L'embedding n'est généralement pas retourné par la query
                    )
                )
        logger.info(f"Pinecone query returned {len(results)} results for query: '{query_text[:50]}...'")
        return results
        
    except Exception as e:
        logger.error(f"Error querying vectors from Pinecone: {e}", exc_info=True)
        # Retourner une liste vide ou remonter l'exception selon la stratégie de gestion d'erreur
        return []