from fastapi import APIRouter, HTTPException, Depends, Path, Query, Body
from typing import List, Optional
from bson import ObjectId
from bson.errors import InvalidId
from database import get_carts_collection, get_products_collection, get_users_collection
from models.cart import CartCreate, CartResponse, Cart, CartItemAdd, CartItemUpdate
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import UpdateOne

router = APIRouter(
    prefix="/carts",
    tags=["Carts"],
    responses={404: {"description": "Not found"}},
)

# Create a shopping cart
@router.post("/", response_model=CartResponse)
async def create_cart(
    cart: CartCreate,
    carts_collection: AsyncIOMotorCollection = Depends(get_carts_collection),
    users_collection: AsyncIOMotorCollection = Depends(get_users_collection)
):
    # Validate user exists
    if not ObjectId.is_valid(cart.user_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid user ID format: {cart.user_id}"
        )
    
    user = await users_collection.find_one({"_id": ObjectId(cart.user_id)})
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with ID {cart.user_id} not found"
        )
    
    # Check if user already has a cart
    existing_cart = await carts_collection.find_one({"user_id": cart.user_id})
    if existing_cart:
        raise HTTPException(
            status_code=400,
            detail=f"User with ID {cart.user_id} already has a cart"
        )
    
    # Create cart
    cart_data = {
        "user_id": cart.user_id,
        "items": []
    }
    
    result = await carts_collection.insert_one(cart_data)
    cart_id = str(result.inserted_id)
    
    # Update user with cart_id
    await users_collection.update_one(
        {"_id": ObjectId(cart.user_id)},
        {"$set": {"cart_id": cart_id}}
    )
    
    return CartResponse(id=cart_id, **cart_data)

# Get a shopping cart by ID
@router.get("/{cart_id}", response_model=CartResponse)
async def get_cart(
    cart_id: str,
    carts_collection: AsyncIOMotorCollection = Depends(get_carts_collection)
):
    if not ObjectId.is_valid(cart_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cart ID format: {cart_id}"
        )
    
    cart = await carts_collection.find_one({"_id": ObjectId(cart_id)})
    if not cart:
        raise HTTPException(
            status_code=404,
            detail=f"Cart with ID {cart_id} not found"
        )
    
    return CartResponse(id=str(cart["_id"]), user_id=cart["user_id"], items=cart["items"])

# Add item to a shopping cart
@router.post("/{cart_id}/items", response_model=CartResponse)
async def add_item_to_cart(
    cart_id: str,
    item: CartItemAdd,
    carts_collection: AsyncIOMotorCollection = Depends(get_carts_collection),
    products_collection: AsyncIOMotorCollection = Depends(get_products_collection)
):
    # Validate the cart ID
    if not ObjectId.is_valid(cart_id):
        raise HTTPException(status_code=400, detail="Invalid cart ID format")
    
    # Validate the product ID
    if not ObjectId.is_valid(item.product_id):
        raise HTTPException(status_code=400, detail="Invalid product ID format")
    
    # Check if the product exists and has enough stock
    product = await products_collection.find_one({"_id": ObjectId(item.product_id)})
    if not product:
        raise HTTPException(status_code=404, detail=f"Product with ID {item.product_id} not found")
    
    # Check if the product is active
    if not product.get("is_active", True):
        raise HTTPException(status_code=400, detail=f"Product with ID {item.product_id} is not available")
    
    # Check if there's enough stock
    if item.quantity > product["stock_quantity"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Not enough stock. Requested: {item.quantity}, Available: {product['stock_quantity']}"
        )
    
    # Try to update an existing item
    result = await carts_collection.update_one(
        {
            "_id": ObjectId(cart_id),
            "items.product_id": item.product_id
        },
        {"$inc": {"items.$.quantity": item.quantity}}
    )

    # If no existing item was updated, add a new one
    if result.modified_count == 0:
        # Check if the cart exists
        cart_exists = await carts_collection.count_documents({"_id": ObjectId(cart_id)}) > 0
        if not cart_exists:
            raise HTTPException(status_code=404, detail=f"Cart with ID {cart_id} not found")
        
        # Add new item
        result = await carts_collection.update_one(
            {"_id": ObjectId(cart_id)},
            {"$push": {"items": item.model_dump()}}
        )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Failed to update cart")
    
    # Update the product's stock quantity
    new_stock = product["stock_quantity"] - item.quantity
    await products_collection.update_one(
        {"_id": ObjectId(item.product_id)},
        {"$set": {"stock_quantity": new_stock}}
    )
    
    # If stock becomes zero, set the product as inactive
    if new_stock == 0:
        await products_collection.update_one(
            {"_id": ObjectId(item.product_id)},
            {"$set": {"is_active": False}}
        )
    
    # Return the updated cart
    updated_cart = await carts_collection.find_one({"_id": ObjectId(cart_id)})
    return CartResponse(id=str(updated_cart["_id"]), user_id=updated_cart["user_id"], items=updated_cart["items"])

# Remove item from a shopping cart
@router.delete("/{cart_id}/items/{product_id}", response_model=CartResponse)
async def remove_item_from_cart(
    cart_id: str,
    product_id: str,
    carts_collection: AsyncIOMotorCollection = Depends(get_carts_collection),
    products_collection: AsyncIOMotorCollection = Depends(get_products_collection)
):
    # Validate IDs
    if not ObjectId.is_valid(cart_id) or not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    # Find the cart and get the item quantity in a single operation
    pipeline = [
        {"$match": {"_id": ObjectId(cart_id)}},
        {"$project": {
            "user_id": 1,
            "items": 1,
            "item_to_remove": {
                "$filter": {
                    "input": "$items",
                    "as": "item",
                    "cond": {"$eq": ["$$item.product_id", product_id]}
                }
            }
        }}
    ]
    
    result = await carts_collection.aggregate(pipeline).to_list(1)
    if not result:
        raise HTTPException(status_code=404, detail=f"Cart with ID {cart_id} not found")
    
    cart = result[0]
    items_to_remove = cart.get("item_to_remove", [])
    
    if not items_to_remove:
        raise HTTPException(status_code=404, detail=f"Item with product ID {product_id} not found in cart")
    
    # Get the quantity to restore
    quantity_to_restore = items_to_remove[0]["quantity"]
    
    # Remove the item from the cart
    update_result = await carts_collection.update_one(
        {"_id": ObjectId(cart_id)},
        {"$pull": {"items": {"product_id": product_id}}}
    )
    
    if update_result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Failed to remove item from cart")
    
    # Restore the product's stock quantity
    await products_collection.update_one(
        {"_id": ObjectId(product_id)},
        {"$inc": {"stock_quantity": quantity_to_restore}}
    )
    
    # If the product was inactive due to zero stock, make it active again
    await products_collection.update_one(
        {"_id": ObjectId(product_id), "stock_quantity": {"$gt": 0}, "is_active": False},
        {"$set": {"is_active": True}}
    )
    
    # Return the updated cart
    updated_cart = await carts_collection.find_one({"_id": ObjectId(cart_id)})
    return CartResponse(id=str(updated_cart["_id"]), user_id=updated_cart["user_id"], items=updated_cart["items"])

# Update item quantity in cart
@router.put("/{cart_id}/items/{product_id}", response_model=CartResponse)
async def update_item_quantity(
    cart_id: str,
    product_id: str,
    item_update: CartItemUpdate,
    carts_collection: AsyncIOMotorCollection = Depends(get_carts_collection),
    products_collection: AsyncIOMotorCollection = Depends(get_products_collection)
):
    # Validate IDs
    if not ObjectId.is_valid(cart_id) or not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    # Get the product to check stock
    product = await products_collection.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")
    
    # Get the current item quantity from the cart
    cart_with_item = await carts_collection.find_one(
        {"_id": ObjectId(cart_id)},
        {"items": {"$elemMatch": {"product_id": product_id}}}
    )
    
    if not cart_with_item:
        raise HTTPException(status_code=404, detail=f"Cart with ID {cart_id} not found")
    
    if not cart_with_item.get("items"):
        raise HTTPException(status_code=404, detail=f"Item with product ID {product_id} not found in cart")
    
    current_quantity = cart_with_item["items"][0]["quantity"]
    quantity_change = item_update.quantity - current_quantity
    
    # Check if there's enough stock for an increase in quantity
    if quantity_change > 0 and quantity_change > product["stock_quantity"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Not enough stock. Additional needed: {quantity_change}, Available: {product['stock_quantity']}"
        )
    
    # Update the item quantity in the cart
    result = await carts_collection.update_one(
        {"_id": ObjectId(cart_id), "items.product_id": product_id},
        {"$set": {"items.$.quantity": item_update.quantity}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Failed to update item quantity")
    
    # Update the product's stock quantity
    new_stock = product["stock_quantity"] - quantity_change
    await products_collection.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": {"stock_quantity": new_stock}}
    )
    
    # Update product active status based on stock
    if new_stock == 0:
        await products_collection.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": {"is_active": False}}
        )
    elif new_stock > 0 and not product.get("is_active", True):
        await products_collection.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": {"is_active": True}}
        )
    
    # Return the updated cart
    updated_cart = await carts_collection.find_one({"_id": ObjectId(cart_id)})
    return CartResponse(id=str(updated_cart["_id"]), user_id=updated_cart["user_id"], items=updated_cart["items"])

# Clear a shopping cart
@router.delete("/{cart_id}/items", response_model=CartResponse)
async def clear_cart(
    cart_id: str,
    carts_collection: AsyncIOMotorCollection = Depends(get_carts_collection),
    products_collection: AsyncIOMotorCollection = Depends(get_products_collection)
):
    # Validate cart ID format
    if not ObjectId.is_valid(cart_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cart ID format: {cart_id}"
        )
    
    # Get cart items in a single query
    cart = await carts_collection.find_one(
        {"_id": ObjectId(cart_id)}
    )
    
    if not cart:
        raise HTTPException(
            status_code=404,
            detail=f"Cart with ID {cart_id} not found"
        )
    
    items_to_restore = cart.get("items", [])
    if not items_to_restore:
        # Cart is already empty, just return it
        return CartResponse(id=str(cart["_id"]), user_id=cart["user_id"], items=[])
    
    # Group items by product_id to minimize database operations
    product_quantities = {}
    for item in items_to_restore:
        product_id = item["product_id"]
        quantity = item["quantity"]
        product_quantities[product_id] = product_quantities.get(product_id, 0) + quantity
    
    # Clear cart items
    await carts_collection.update_one(
        {"_id": ObjectId(cart_id)},
        {"$set": {"items": []}}
    )
    
    # Update each product individually
    for product_id, quantity in product_quantities.items():
        # Update stock quantity
        await products_collection.update_one(
            {"_id": ObjectId(product_id)},
            {"$inc": {"stock_quantity": quantity}}
        )
        
        # Set product as active if it was inactive due to zero stock
        await products_collection.update_one(
            {"_id": ObjectId(product_id), "stock_quantity": {"$gt": 0}, "is_active": False},
            {"$set": {"is_active": True}}
        )
    
    # Return the updated cart (we already know it's empty)
    return CartResponse(id=str(cart["_id"]), user_id=cart["user_id"], items=[])

# Delete a shopping cart
@router.delete("/{cart_id}")
async def delete_cart(
    cart_id: str,
    carts_collection: AsyncIOMotorCollection = Depends(get_carts_collection),
    users_collection: AsyncIOMotorCollection = Depends(get_users_collection),
    products_collection: AsyncIOMotorCollection = Depends(get_products_collection)
):
    # Validate cart ID format
    if not ObjectId.is_valid(cart_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cart ID format: {cart_id}"
        )
    
    # Get the cart with its items
    cart = await carts_collection.find_one({"_id": ObjectId(cart_id)})
    if not cart:
        raise HTTPException(
            status_code=404,
            detail=f"Cart with ID {cart_id} not found"
        )
    
    # Get the user associated with this cart
    user = await users_collection.find_one({"cart_id": cart_id})
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User associated with cart ID {cart_id} not found"
        )
    
    user_id = str(user["_id"])
    
    # 1. Update stock quantities for all items in the cart (finalize purchase)
    items = cart.get("items", [])
    
    # Group items by product_id to minimize database operations
    product_quantities = {}
    for item in items:
        product_id = item["product_id"]
        quantity = item["quantity"]
        product_quantities[product_id] = product_quantities.get(product_id, 0) + quantity
    
    # Update each product's stock
    for product_id, quantity in product_quantities.items():
        # Verify product exists and has enough stock
        product = await products_collection.find_one({"_id": ObjectId(product_id)})
        if not product:
            continue  # Skip if product doesn't exist
            
        # Ensure we don't go below zero stock
        new_stock = max(0, product["stock_quantity"] - quantity)
        
        # Update stock quantity
        await products_collection.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": {"stock_quantity": new_stock}}
        )
        
        # If stock becomes zero, set the product as inactive
        if new_stock == 0:
            await products_collection.update_one(
                {"_id": ObjectId(product_id)},
                {"$set": {"is_active": False}}
            )
    
    # 2. Remove the cart ID from the user document
    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$unset": {"cart_id": ""}}
    )
    
    # 3. Create a new empty cart for the user
    new_cart_data = {
        "user_id": user_id,
        "items": []
    }
    
    new_cart_result = await carts_collection.insert_one(new_cart_data)
    new_cart_id = str(new_cart_result.inserted_id)
    
    # Update user with the new cart ID
    update_result = await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"cart_id": new_cart_id}}
    )

    # Debug: Verify the update was successful
    if update_result.modified_count == 0:
        print(f"WARNING: Failed to update user {user_id} with new cart ID {new_cart_id}")
    else:
        print(f"Successfully updated user {user_id} with new cart ID {new_cart_id}")

    # Debug: Verify the user document after update
    updated_user = await users_collection.find_one({"_id": ObjectId(user_id)})
    print(f"User after update: {updated_user}")
    
    # 4. Delete the old cart
    await carts_collection.delete_one({"_id": ObjectId(cart_id)})
    
    return {
        "message": f"Cart with ID {cart_id} checked out successfully",
        "new_cart_id": new_cart_id
    } 