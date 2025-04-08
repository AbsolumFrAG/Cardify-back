import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import re
import json
from typing import List, Dict, Any
from api.config.settings import get_settings
import logging

logger = logging.getLogger(__name__)

settings = get_settings()

# Configure the Gemini client
genai.configure(api_key=settings.gemini_api_key)

# --- Configuration des modèles Gemini ---
# Pour l'extraction de texte et la génération de flashcards
GENERATION_MODEL_NAME = "gemini-2.0-flash"
# Pour les embeddings (vérifiez la disponibilité et le nom exact)
EMBEDDING_MODEL_NAME = "gemini-embedding-exp-03-07"
# Dimension des embeddings pour le modèle choisi (gemini-embedding-exp-03-07 -> 8000)
EMBEDDING_DIMENSION = 8000

# Configuration de sécurité pour les générations
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

# Configuration de génération par défaut
DEFAULT_GENERATION_CONFIG = genai.GenerationConfig(
    response_mime_type="text/plain",
)

# Modèle génératif (texte, vision)
generative_model = genai.GenerativeModel(
    GENERATION_MODEL_NAME,
    safety_settings=SAFETY_SETTINGS,
    generation_config=DEFAULT_GENERATION_CONFIG
)

# Modèle d'embedding
embedding_model = genai.GenerativeModel(EMBEDDING_MODEL_NAME)

async def extract_text_from_image(image_base64: str) -> Dict[str, Any]:
    """
    Extract text from an image using Gemini Vision API.

    Args:
        image_base64: Base64 encoded image data (without the data:image/... prefix).

    Returns:
        Dictionary containing extracted text, success status, and optional error message.
    """
    try:
        # Prépare l'image pour l'API Gemini
        image_part = {
            "mime_type": "image/jpeg",
            "data": image_base64
        }
        
        prompt = "Extrais tout le texte de cette image de notes de cours. Réponds uniquement avec le texte extrait. Si tu ne peux pas extraire de texte, réponds seulement avec 'EXTRACTION_IMPOSSIBLE'."

        # Génère le contenu en utilisant le modèle multimodal
        response = await generative_model.generate_content_async([prompt, image_part])

        # Vérifie si la réponse a été bloquée ou n'a pas de texte
        if not response.parts:
            # Essayer d'obtenir la raison du blocage si disponible
            block_reason = response.prompt_feedback.block_reason if response.prompt_feedback else "Inconnue"
            error_message = f"L'extraction a été bloquée ou a échoué. Raison: {block_reason}"
            logger.warning(f"Gemini text extraction failed or blocked: {error_message}")
            return {
                "text": "",
                "success": False,
                "error_message": error_message,
            }

        extracted_text = response.text.strip()

        if extracted_text == "EXTRACTION_IMPOSSIBLE" or not extracted_text:
            logger.info("Gemini could not extract text or returned EXTRACTION_IMPOSSIBLE.")
            return {
                "text": "",
                "success": False,
                "error_message": "Impossible d'extraire du texte de cette image",
            }
        
        logger.info("Gemini successfully extracted text from image.")
        return {
            "text": extracted_text,
            "success": True,
        }
    except Exception as e:
        logger.error(f"Error extracting text from image with Gemini: {e}", exc_info=True)
        return {
            "text": "",
            "success": False,
            "error_message": f"Erreur lors de la communication avec l'API Gemini Vision: {str(e)}",
        }

async def generate_flashcards(text: str, num_cards: int = 5) -> List[Dict[str, str]]:
    """
    Generate flashcards from text using Gemini.

    Args:
        text: The source text for flashcards.
        num_cards: The desired number of flashcards.

    Returns:
        A list of dictionaries, each representing a flashcard {'question': '...', 'answer': '...'}.
    """
    prompt = f"""Génère exactement {num_cards} flashcards pertinentes au format question/réponse à partir du texte de cours suivant.
Format de sortie attendu : Uniquement un tableau JSON valide contenant des objets avec les clés "question" et "answer". Exemple : `[{"question": "...", "answer": "..."}]`

Texte de cours :
---
{text}
---

Réponds seulement avec le tableau JSON. Ne rajoute aucun texte avant ou après le JSON.
"""
    try:
        # Configuration spécifique pour demander du JSON (si le modèle le supporte)
        json_generation_config = genai.GenerationConfig(response_mime_type="application/json")
        
        # Utiliser le modèle génératif standard (pas besoin de vision ici)
        text_model = genai.GenerativeModel(
            GENERATION_MODEL_NAME,
            safety_settings=SAFETY_SETTINGS,
            generation_config=json_generation_config # Essayer de forcer le JSON
        )
        
        response = await text_model.generate_content_async(prompt)

        if not response.parts:
            block_reason = response.prompt_feedback.block_reason if response.prompt_feedback else "Inconnue"
            error_message = f"La génération de flashcards a été bloquée ou a échoué. Raison: {block_reason}"
            logger.warning(f"Gemini flashcard generation failed or blocked: {error_message}")
            return []
            
        content = response.text.strip()
        
        # Essayer d'extraire le JSON de la réponse
        # Gemini peut parfois ajouter des ```json ... ``` autour
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```|(\[[\s\S]*\])', content, re.DOTALL)
        
        if json_match:
            json_str = json_match.group(1) or json_match.group(2)
            try:
                flashcards = json.loads(json_str)
                # Valider le format
                if isinstance(flashcards, list) and all(isinstance(fc, dict) and 'question' in fc and 'answer' in fc for fc in flashcards):
                    logger.info(f"Gemini successfully generated {len(flashcards)} flashcards.")
                    return flashcards
                else:
                    logger.warning(f"Gemini response format for flashcards is invalid: {flashcards}")
                    return []
            except json.JSONDecodeError as json_err:
                logger.error(f"Failed to decode JSON from Gemini flashcard response: {json_err}\nResponse: {content}")
                return []
        else:
            logger.warning(f"Could not find valid JSON in Gemini flashcard response: {content}")
            return []

    except Exception as e:
        logger.error(f"Error generating flashcards with Gemini: {e}", exc_info=True)
        return []
    
async def create_embedding(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> List[float]:
    """
    Create embeddings for text using Gemini Embedding API.

    Args:
        text: The text to embed.
        task_type: Type of task (e.g., "RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY", "SEMANTIC_SIMILARITY").

    Returns:
        A list of floats representing the embedding.

    Raises:
        Exception: If embedding creation fails.
    """
    try:
        # Utilise l'API d'embedding spécifique
        result = await genai.embed_content_async(
            model=EMBEDDING_MODEL_NAME,
            content=text,
            task_type=task_type # Important pour optimiser l'embedding
        )
        
        # Vérifie si l'embedding a été généré
        if "embedding" not in result or not result["embedding"]:
             logger.error("Gemini embedding API did not return an embedding.")
             raise ValueError("Failed to generate embedding, response did not contain embedding.")

        logger.debug(f"Gemini successfully created embedding for task type {task_type}.")
        return result["embedding"]
    
    except Exception as e:
        logger.error(f"Error creating embedding with Gemini: {e}", exc_info=True)
        # Remonter l'exception pour que l'appelant puisse la gérer
        raise ValueError(f"Error creating embedding with Gemini: {str(e)}") from e
    
async def generate_answer_with_rag(question: str, context: str) -> str:
    """
    Generate an answer using RAG with Gemini, based on provided context.

    Args:
        question: The user's question.
        context: Relevant text chunks retrieved from the vector store.

    Returns:
        The generated answer string.
    """
    prompt = f"""Tu es un assistant pédagogique expert qui aide les étudiants à comprendre leurs cours en se basant **strictement** sur les notes fournies.
Réponds de manière concise, claire et précise à la question de l'étudiant en utilisant uniquement les informations présentes dans le contexte ci-dessous.
Si le contexte ne contient pas la réponse, indique poliment que l'information n'est pas disponible dans les notes fournies. Ne spécule pas et n'ajoute pas d'informations externes.

Contexte des notes de cours :
---
{context}
---

Question de l'étudiant : {question}

Réponse basée sur le contexte :
"""
    try:
        # Utiliser le modèle génératif standard
        response = await generative_model.generate_content_async(prompt)

        if not response.parts:
            block_reason = response.prompt_feedback.block_reason if response.prompt_feedback else "Inconnue"
            error_message = f"La génération de réponse RAG a été bloquée ou a échoué. Raison: {block_reason}"
            logger.warning(f"Gemini RAG answer generation failed or blocked: {error_message}")
            return "Désolé, une erreur est survenue lors de la génération de la réponse."
            
        answer = response.text.strip()
        logger.info("Gemini successfully generated RAG answer.")
        return answer if answer else "Désolé, je n'ai pas pu générer une réponse à cette question en me basant sur le contexte fourni."

    except Exception as e:
        logger.error(f"Error generating RAG answer with Gemini: {e}", exc_info=True)
        return "Désolé, une erreur technique m'empêche de répondre à cette question pour le moment."