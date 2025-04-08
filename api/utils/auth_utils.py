from typing import Dict, Any, Optional
from supabase import create_client, Client
from api.config.settings import get_settings

settings = get_settings()

supabase: Client = create_client(
    settings.supabase_url,
    settings.supabase_key
)

async def sign_up_user(email: str, password: str, full_name: Optional[str] = None) -> Dict[str, Any]:
    """Register a new user using Supabase Auth"""
    try:
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "full_name": full_name
                } if full_name else {}
            }
        })

        if auth_response.error:
            raise ValueError(auth_response.error.message)
        
        return {
            "access_token": auth_response.session.access_token,
            "user": {
                "id": auth_response.user.id,
                "email": auth_response.user.email,
            }
        }
    except Exception as e:
        if hasattr(e, "message"):
            raise ValueError(e.message)
        raise ValueError(f"Error during signup: {str(e)}")
    
async def sign_in_user(email: str, password: str) -> Dict[str, Any]:
    """Sign in a user using Supabase Auth"""
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if auth_response.error:
            raise ValueError(auth_response.error.message)
        
        return {
            "access_token": auth_response.session.access_token,
            "user": {
                "id": auth_response.user.id,
                "email": auth_response.user.email,
            }
        }
    except Exception as e:
        if hasattr(e, "message"):
            raise ValueError(e.message)
        raise ValueError(f"Error during login: {str(e)}")
    
async def get_user_profile(token: str) -> Dict[str, Any]:
    """Get user profile using Supabase Auth"""
    try:
        supabase.auth.set_session(token)

        user_response = supabase.auth.get_user()

        if user_response.error:
            raise ValueError(user_response.error.message)
        
        user = user_response.user

        return {
            "id": user.id,
            "email": user.email,
            "user_metadata": user.user_metadata
        }
    except Exception as e:
        if hasattr(e, "message"):
            raise ValueError(e.message)
        raise ValueError(f"Error getting user profile: {str(e)}")
    
async def verify_token(token: str) -> Dict[str, Any]:
    """Verify JWT token using Supabase Auth"""
    try:
        user_data = await get_user_profile(token)
        return user_data
    except Exception as e:
        raise ValueError(f"Invalid or expired token: {str(e)}")