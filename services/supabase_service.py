from supabase import create_client, Client
from config import get_settings
from typing import Dict, Any, Optional
from fastapi import HTTPException, status

settings = get_settings()

def get_supabase_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_key)

async def sign_up_user(email: str, password: str) -> Dict[str, Any]:
    client = get_supabase_client()
    try:
        result = client.auth.sign_up({
            "email": email,
            "password": password
        })
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur d'inscription: {str(e)}"
        )
    
async def sign_in_user(email: str, password: str) -> Dict[str, Any]:
    client = get_supabase_client()
    try:
        result = client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides"
        )
    
async def sign_in_with_google(token: str) -> Dict[str, Any]:
    client = get_supabase_client()
    try:
        result = client.auth.sign_in_with_oauth({
            "provider": "google",
            "access_token": token
        })
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Google invalide"
        )
    
async def get_user(token: str) -> Optional[Dict[str, Any]]:
    client = get_supabase_client()
    try:
        user = client.auth.get_user(token)
        return user
    except Exception:
        return None