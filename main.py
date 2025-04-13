from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, flashcards, ai
from lifespan import lifespan

app = FastAPI(
    title="API Cardify",
    description="API de Cardify",
    version="1.0.0",
    lifespan=lifespan
)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À limiter en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion des routers
app.include_router(auth.router, prefix="/auth", tags=["Authentification"])
app.include_router(flashcards.router, prefix="/flashcards", tags=["Flashcards"])
app.include_router(ai.router, prefix="/ai", tags=["IA"])

@app.get("/")
async def root():
    return {"message": "Bienvenue sur l'API de génération de flashcards"}