from contextlib import asynccontextmanager
from fastapi import FastAPI
import google.generativeai as genai
from config import get_settings

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Logique de démarrage
    print("Démarrage de l'application...")
    # Initialisation de l'API Gemini
    genai.configure(api_key=settings.gemini_api_key)
    
    yield
    
    # Logique d'arrêt
    print("Arrêt de l'application...")
    # Nettoyage des ressources