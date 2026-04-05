from pydantic import BaseModel, EmailStr
from typing import Optional, List

class GuardianRegisterRequest(BaseModel):
    """Guardian registration data"""
    name: str
    phone: Optional[str] = None

class GuardianProfileResponse(BaseModel):
    """Guardian profile response"""
    guardian_id: str
    email: str
    name: str
    phone: Optional[str]
    created_at: str
    monitored_users: List[str]

class LinkUserRequest(BaseModel):
    """Request to link guardian to blind user"""
    user_unique_id: str