from typing import Optional, List, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId

# Base input/output models
class UserBase(BaseModel):
    name: str
    email: EmailStr

class User(UserBase):
    id: str = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}

    
# Input models
class UserCreate(UserBase):
    pass

# Output model
class UserResponse(UserBase):
    id: str

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    skip: int
    limit: int
    has_more: bool 