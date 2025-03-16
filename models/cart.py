from typing import List, Optional
from pydantic import BaseModel, Field
from bson import ObjectId

class CartItem(BaseModel):
    product_id: str = Field(..., description="Reference to the product")
    quantity: int = Field(..., gt=0, description="Number of units of the product")

class CartBase(BaseModel):
    user_id: str = Field(..., description="Reference to the associated user")
    items: List[CartItem] = Field(default_factory=list, description="Items in the cart")

class Cart(CartBase):
    id: str = Field(alias="_id")
    
    class Config:
        json_encoders = {ObjectId: str}
        populate_by_name = True

# Input models
class CartCreate(BaseModel):
    user_id: str

class CartItemAdd(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0)

class CartItemUpdate(BaseModel):
    quantity: int = Field(..., gt=0)

# Output models
class CartResponse(CartBase):
    id: str 