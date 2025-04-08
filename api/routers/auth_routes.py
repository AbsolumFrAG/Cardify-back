from fastapi import APIRouter, HTTPException, Depends
from api.schemas.auth_schemas import UserSignUp, UserCredentials, UserToken, UserProfile
from api.utils.auth_utils import sign_up_user, sign_in_user, get_user_profile
from api.middlewares.auth_middleware import get_current_user
from typing import Dict, Any

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserToken)
async def register_user(user_data: UserSignUp) -> UserToken:
    """Register a new user"""
    try:
        result = await sign_up_user(user_data.email, user_data.password, user_data.full_name)

        return UserToken(
            access_token=result["access_token"],
            user_id=result["user"]["id"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")
    
@router.post("/login", response_model=UserToken)
async def login_user(credentials: UserCredentials) -> UserToken:
    """Login a user"""
    try:
        result = await sign_in_user(credentials.email, credentials.password)

        return UserToken(
            access_token=result["access_token"],
            user_id=result["user"]["id"],
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")
    
@router.get("/profile", response_model=UserProfile)
async def get_profile(current_user: Dict[str, Any] = Depends(get_current_user)) -> UserProfile:
    """Get user profile"""
    return UserProfile(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user.get("user_metadata", {}).get("full_name")
    )