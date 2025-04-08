import chromadb
from chromadb import Collection
from chromadb.config import Settings as ChromaSettings
from typing import List
from api.config.settings import get_settings as get_app_settings 
from api.utils.gemini_utils import create_embedding, EMBEDDING_DIMENSION 
from api.schemas.content_schemas import ContentChunk
import logging

logger = logging.getLogger(__name__) 

# Obtenir les paramètres de l'application
app_settings = get_app_settings()

# Configuration et initialisation du client ChromaDB HTTP
try:
    # Supprimer la création de dossier local
    # os.makedirs(app_settings.chroma_db_path, exist_ok=True)
    
    # Configurer et créer le client HTTP
    client = chromadb.HttpClient(
        host=app_settings.chroma_server_host,
        port=app_settings.chroma_server_port,
        settings=ChromaSettings(anonymized_telemetry=False) 
    )

    # Vérifier la connexion (heartbeat)
    client.heartbeat() # Lance une exception si la connexion échoue

    # Obtenir ou créer la collection (même logique qu'avant)
    collection: Collection = client.get_or_create_collection(
        name=app_settings.chroma_collection_name,
    )
    logger.info(f"ChromaDB HTTP client connected to {app_settings.chroma_server_host}:{app_settings.chroma_server_port}. Using collection: '{collection.name}'")

except Exception as e:
    logger.error(f"Erreur lors de l'initialisation ou de la connexion au serveur ChromaDB distant: {e}", exc_info=True)
    raise RuntimeError(f"Impossible de se connecter au serveur ChromaDB à {app_settings.chroma_server_host}:{app_settings.chroma_server_port} : {e}") from e

# --- Les fonctions upsert_vector et query_vectors restent les mêmes ---
# Elles utilisent l'objet 'collection' qui est maintenant connecté au serveur distant.

async def upsert_vector(chunk: ContentChunk) -> None:
    """Add or update a vector in the remote ChromaDB."""
    try:
        if not chunk.embedding:
            logger.debug(f"Génération de l'embedding pour le chunk ID: {chunk.id} (tâche: RETRIEVAL_DOCUMENT)")
            chunk.embedding = await create_embedding(chunk.text, task_type="RETRIEVAL_DOCUMENT") 

        if len(chunk.embedding) != EMBEDDING_DIMENSION:
             logger.error(f"Dimension d'embedding incorrecte pour chunk {chunk.id}. Attendu: {EMBEDDING_DIMENSION}, Obtenu: {len(chunk.embedding)}")
             raise ValueError(f"Dimension d'embedding incorrecte générée pour le chunk {chunk.id}.")

        metadata_to_upsert = {
            k: str(v) if v is not None and not isinstance(v, (str, int, float, bool)) else v 
            for k, v in chunk.metadata.items()
        }
        
        logger.debug(f"Upserting vector ID: {chunk.id} into remote ChromaDB collection: {collection.name}")
        
        collection.upsert(
            ids=[chunk.id],
            embeddings=[chunk.embedding],
            metadatas=[metadata_to_upsert],
            documents=[chunk.text] 
        )
        logger.info(f"Vector upserted successfully to remote ChromaDB for ID: {chunk.id}")

    except ValueError as ve: 
        logger.error(f"Erreur de valeur lors de l'upsert ChromaDB distant pour ID {chunk.id}: {ve}", exc_info=True)
        raise ve 
    except Exception as e:
        # Les erreurs peuvent maintenant être liées à la connexion réseau aussi
        logger.error(f"Error upserting vector ID {chunk.id} to remote ChromaDB: {e}", exc_info=True)
        raise RuntimeError(f"Erreur lors de l'upsert ChromaDB distant pour ID {chunk.id}: {e}") from e

async def query_vectors(query_text: str, top_k: int = 5, user_id: str | None = None) -> List[ContentChunk]:
    """Query similar vectors from the remote ChromaDB, optionally filtering by user_id."""
    try:
        logger.debug(f"Génération de l'embedding pour la requête ChromaDB distante (tâche: RETRIEVAL_QUERY): '{query_text[:50]}...'")
        query_embedding = await create_embedding(query_text, task_type="RETRIEVAL_QUERY")

        where_filter = None
        if user_id:
            where_filter = {"user_id": str(user_id)} # Assurer string
            logger.debug(f"Applying ChromaDB where filter: {where_filter}")
        
        logger.debug(f"Querying remote ChromaDB collection '{collection.name}' with top_k={top_k}")
        
        query_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter, 
            include=['metadatas', 'documents', 'distances'] 
        )

        results = []
        if query_results and query_results.get('ids') and query_results['ids'][0]:
            ids = query_results['ids'][0]
            documents = query_results['documents'][0]
            metadatas = query_results['metadatas'][0]
            distances = query_results['distances'][0] 

            for i in range(len(ids)):
                score = distances[i] 
                results.append(
                    ContentChunk(
                        id=ids[i],
                        text=documents[i], 
                        metadata=metadatas[i], 
                        score=score 
                    )
                )
        
        logger.info(f"Remote ChromaDB query returned {len(results)} results for query: '{query_text[:50]}...'")
        return results
        
    except Exception as e:
        # Les erreurs peuvent maintenant être liées à la connexion réseau aussi
        logger.error(f"Error querying vectors from remote ChromaDB: {e}", exc_info=True)
        return [] 