from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from api.routers import auth_routes, ai_routes, vector_store_routes, transcription_routes 
from api.middlewares.error_handler import ErrorHandlerMiddleware
import logging
from api.config.settings import get_settings 
from api.utils import chromadb_utils 

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(name)s [%(levelname)s] - %(message)s",
    handlers=[
        logging.StreamHandler() 
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting up the application...")
    try:
        # Essayer d'obtenir les settings pour vérifier la configuration
        settings = get_settings() 
        logger.info("Settings loaded successfully.")
        # Initialiser explicitement ChromaDB HttpClient ici
        _ = chromadb_utils.client # Accéder au client pour forcer l'initialisation et le heartbeat initial
        logger.info(f"ChromaDB HTTP client connection to {settings.chroma_server_host}:{settings.chroma_server_port} successful via lifespan.")
    except Exception as e:
        logger.critical(f"Application startup failed during settings or ChromaDB connection: {e}", exc_info=True)
        raise RuntimeError(f"Startup failed: {e}") from e
    
    yield
    # Shutdown logic
    logger.info("Shutting down the application.")
    # Pas de nettoyage spécifique nécessaire pour HttpClient généralement

# Create the FastAPI application
app = FastAPI(
    title="Cardify App API with Gemini & Remote ChromaDB",
    description="API for the Cardify App with Google Gemini and Remote ChromaDB integration",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
allowed_origins = ["*"] # À remplacer en production
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins, 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# Add error handler middleware
app.add_middleware(ErrorHandlerMiddleware)

# Include routers
app.include_router(auth_routes.router)
app.include_router(ai_routes.router) 
app.include_router(vector_store_routes.router)
app.include_router(transcription_routes.router)

@app.get("/health", tags=["Health Check"])
async def health_check():
    """Health check endpoint to verify the API is running and connected to ChromaDB"""
    # Vérifier la connexion ChromaDB
    chroma_status = "ok"
    chroma_error = None
    try:
        # client.heartbeat() vérifie si le serveur distant répond
        chromadb_utils.client.heartbeat() 
    except Exception as e:
        logger.error(f"ChromaDB remote server health check failed: {e}")
        chroma_status = "error"
        chroma_error = str(e)
        
    return {
        "status": "ok", 
        "message": "API is running", 
        "chromadb_connection": {
            "status": chroma_status,
            "host": get_settings().chroma_server_host,
            "port": get_settings().chroma_server_port,
            "error": chroma_error if chroma_error else None
        }
    }

# Configuration pour Uvicorn (si lancé directement)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True, # Désactiver reload en production
        log_level="info" 
    )