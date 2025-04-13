from fastapi import APIRouter, HTTPException, status
from models.flashcard import UserSignUp, UserSignIn, GoogleSignIn
from services.supabase_service import sign_up_user, sign_in_user, sign_in_with_google

router = APIRouter()

@router.post("/signup")
async def signup(user_data: UserSignUp):
    try:
        result = await sign_up_user(user_data.email, user_data.password)
        return {"message": "Utilisateur enregistré avec succès", "user": result.user}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    
@router.post("/login")
async def login(user_data: UserSignIn):
    try:
        result = await sign_in_user(user_data.email, user_data.password)
        return {
            "access_token": result.session.access_token,
            "user": result.user
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    
@router.post("/google")
async def google_login(data: GoogleSignIn):
    try:
        result = await sign_in_with_google(data.token)
        return {
            "access_token": result.session.access_token,
            "user": result.user
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )