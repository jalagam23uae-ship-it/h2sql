"""User model for authentication"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserModel(BaseModel):
    """User model for authentication and authorization"""
    id: Optional[int] = None
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = False
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
