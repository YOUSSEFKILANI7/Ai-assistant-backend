from pydantic import BaseModel
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


class BlindUserRegisterRequest(BaseModel):
    """Blind user profile registration data"""
    unique_id: str
    name: str
    device_id: Optional[str] = None


class BlindUserAdminCreateRequest(BaseModel):
    """Admin creates blind user auth + profile seed"""
    blind_user_email: str
    blind_user_password: str
    unique_id: str
    name: str
    device_id: Optional[str] = None


class BlindUserProfileResponse(BaseModel):
    """Blind user profile response"""
    unique_id: str
    auth_uid: str
    email: str
    name: str
    device_id: Optional[str]
    active: bool
    created_at: str
    linked_guardians: List[str]


class GuardianInviteRequest(BaseModel):
    """Blind user invites guardian by email"""
    guardian_email: str


class GuardianInviteResponse(BaseModel):
    """Result of creating a guardian invitation"""
    status: str
    guardian_email: str
    guardian_id: str
    blind_user_id: str
    email_sent: bool
    message: str
    temporary_password: Optional[str] = None
