import google.generativeai as genai
from typing import List
from config import get_settings
import json
from models.flashcard import FlashcardCreate, Language

settings = get_settings()

# Configuration du client API Gemini
genai.configure(api_key=settings.gemini_api_key)

async def get_gemini_model():
    return genai.GenerativeModel("gemini-pro-vision")

async def extract_text_from_images(image_data_list: List[str]) -> str:
    """Extraire le texte à partir d'une liste d'images encodées en base64."""
    model = await get_gemini_model()

    # Conversion des images encodées en base64 au format attendu par Gemini
    image_parts = []
    for image_data in image_data_list:
        if image_data.startswith("data:image"):
            # Extraire le contenu base64 après la virgule
            image_data = image_data.split(",")[1]

        image_parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": image_data
            }
        })

    # Génération d'un prompt pour extraire le texte des images
    prompt = "Extrais et retourne tout le contenu textuel de ces images. Formate-le clairement et préserve la structure des paragraphes."

    response = await model.generate_content_async([prompt, *image_parts])
    return response.text

async def generate_flashcards(
        image_data_list: List[str],
        count: int,
        language: Language,
        course_name: str = None,
        tags: List[str] = []
) -> List[FlashcardCreate]:
    """Générer des flashcards en utilisant Google Gemini à partir du contenu des images."""
    # Extraction du texte des images
    extracted_text = await extract_text_from_images(image_data_list)

    # Utilisation du texte pour générer des flashcards
    model = genai.GenerativeModel("gemini-pro")

    # Création d'un prompt pour générer des flashcards dans la langue spécifiée
    lang_dict = {
        Language.ENGLISH: "anglais",
        Language.FRENCH: "français",
        Language.SPANISH: "espagnol",
        Language.GERMAN: "allemand",
        Language.ITALIAN: "italien",
        Language.VIETNAMESE: "vietnamien",
        Language.THAI: "thaïlandais"
    }

    language_name = lang_dict.get(language, "français")

    prompt = f"""
    En te basant sur le contenu de cours suivant, crée {count} flashcards en {language_name}.
    Chaque flashcard doit avoir une question et une réponse.
    
    Contenu du cours:
    {extracted_text}
    
    Renvoie les flashcards sous forme de tableau JSON avec la structure suivante:
    [
      {{
        "question": "Question 1",
        "answer": "Réponse 1"
      }},
      {{
        "question": "Question 2",
        "answer": "Réponse 2"
      }}
    ]
    
    Les questions doivent tester les concepts clés, définitions ou applications du contenu.
    Les réponses doivent être concises mais complètes.
    """

    response = await model.generate_content_async(prompt)

    # Extraction du tableau JSON de la réponse
    try:
        # Recherche du JSON dans le texte de réponse
        response_text = response.text
        start_idx = response_text.find('[')
        end_idx = response_text.rfind(']') + 1

        if start_idx >= 0 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            flashcards_data = json.loads(json_str)
        else:
            # Repli si le formatage JSON a échoué
            raise ValueError("Impossible d'extraire le JSON de la réponse")
        
        # Conversion en objets FlashcardCreate
        flashcards = []
        for fc_data in flashcards_data:
            flashcard = FlashcardCreate(
                question=fc_data["question"],
                answer=fc_data["answer"],
                course_name=course_name,
                tags=tags
            )
            flashcards.append(flashcard)

        return flashcards
    
    except Exception as e:
        # Gestion des erreurs d'analyse JSON
        raise ValueError(f"Échec d'analyse des flashcards générées: {str(e)}")