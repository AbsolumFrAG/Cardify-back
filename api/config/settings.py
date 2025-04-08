from pydantic_settings import BaseSettings
from functools import lru_cache
import os 
from dotenv import load_dotenv 

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

class Settings(BaseSettings):
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "") 

    # Configuration Supabase
    supabase_url: str
    supabase_key: str

    # Configuration ChromaDB
    chroma_server_host: str = os.getenv("CHROMA_SERVER_HOST", "localhost") # Hôte de votre serveur ChromaDB sur le VPS
    chroma_server_port: int = int(os.getenv("CHROMA_SERVER_PORT", "8000")) # Port de votre serveur ChromaDB
    chroma_collection_name: str = os.getenv("CHROMA_COLLECTION_NAME", "cardify_content") # Nom de la collection

    class Config:
        env_file_encoding = 'utf-8' 
        extra = 'ignore' 

@lru_cache()
def get_settings():
    settings = Settings()
    if not settings.gemini_api_key:
        raise ValueError("La variable d'environnement GEMINI_API_KEY n'est pas définie.")
    if not settings.chroma_server_host:
        raise ValueError("La variable d'environnement CHROMA_SERVER_HOST n'est pas définie.")
    return settings