from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

class RegisterProfileRequest(BaseModel):
    """
    Data that comes from Flutter app AFTER Firebase creates the account
    """
    name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = None
    role: str = Field(default="visually_impaired_user")  # or "guardian"

class UserProfileResponse(BaseModel):
    """
    What we send back to the app
    """
    user_id: str
    email: str
    name: str
    phone: Optional[str]
    role: str
    created_at: str

class LinkGuardianRequest(BaseModel):
    """
    To link a guardian to a user
    """
    guardian_email: str