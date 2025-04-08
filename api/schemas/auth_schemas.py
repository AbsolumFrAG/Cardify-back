from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserCredentials(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserSignUp(UserCredentials):
    full_name: Optional[str] = None

class UserToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str

class UserProfile(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str] = None