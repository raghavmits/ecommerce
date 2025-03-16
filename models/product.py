from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, computed_field
from bson import ObjectId

class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, description="Product name must be at least 2 characters")
    description: str = Field(..., min_length=10, description="Description must be at least 10 characters")
    price: Decimal = Field(..., gt=0, description="Price must be greater than 0")
    stock_quantity: int = Field(..., ge=0, description="Stock quantity must be 0 or positive")
    category: Optional[str] = Field(None, description="Product category (optional)")
    
    @computed_field
    @property
    def is_active(self) -> bool:
        """Product is active when stock quantity is greater than 0"""
        return self.stock_quantity > 0
    
    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()
    
    @field_validator('description')
    @classmethod
    def description_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Description cannot be empty")
        return v.strip()

class Product(ProductBase):
    id: str = Field(alias="_id")
    
    class Config:
        json_encoders = {ObjectId: str}
        populate_by_name = True

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2)
    description: Optional[str] = Field(None, min_length=10)
    price: Optional[Decimal] = Field(None, gt=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    category: Optional[str] = None
    # Note: is_active is not included here, so it can't be updated directly

# Output model
class ProductResponse(ProductBase):
    id: str 