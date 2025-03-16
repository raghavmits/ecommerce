from typing import Optional
from pydantic import BaseModel, Field, EmailStr, field_validator
from bson import ObjectId

# Base input/output models
class UserBase(BaseModel):
    name: str = Field(..., min_length=2, description="User name must be at least 2 characters")
    email: EmailStr
    
    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

class User(UserBase):
    id: str = Field(alias="_id")
    cart_id: Optional[str] = None  # Reference to the user's shopping cart

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}


# Input models
class UserCreate(UserBase):
    pass

# Output model
class UserResponse(UserBase):
    id: str
    cart_id: Optional[str] = None
    
    class Config:
        populate_by_name = True

# Add this class after UserResponse
class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2)
    email: Optional[EmailStr] = None 