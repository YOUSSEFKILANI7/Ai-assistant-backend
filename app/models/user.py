from pydantic import BaseModel
from typing import Optional, List

class BlindUser(BaseModel):
    unique_id: str
    name: str
    device_id: Optional[str] = None
    active: bool = True
    linked_guardians: List[str] = []

class BlindUserResponse(BaseModel):
    unique_id: str
    name: str
    device_id: Optional[str]
    active: bool
    created_at: str
    guardian_count: int