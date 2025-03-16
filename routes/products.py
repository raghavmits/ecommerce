from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body
from typing import Optional, List
from bson import ObjectId
from bson.errors import InvalidId
from decimal import Decimal
from database import get_products_collection
from models.product import ProductCreate, ProductResponse, Product, ProductUpdate
from models.common import PaginatedResponse
from motor.motor_asyncio import AsyncIOMotorCollection

router = APIRouter(
    prefix="/products",
    tags=["Products"],  # This will group all product routes under "Products" heading
    responses={404: {"description": "Not found"}},
)

def convert_decimal_to_float(data: dict) -> dict:
    """Convert Decimal values to float for MongoDB storage"""
    for key, value in data.items():
        if isinstance(value, Decimal):
            data[key] = float(value)
    return data

def prepare_product_data(product_data: dict) -> dict:
    """
    Prepare product data for response by converting ObjectId to string
    and handling any other necessary conversions
    """
    return {
        **product_data,
        "_id": str(product_data["_id"])  # Convert ObjectId to string
    }

# Create a new product
@router.post("/", response_model=ProductResponse)
async def create_product(
    product: ProductCreate, 
    products_collection: AsyncIOMotorCollection = Depends(get_products_collection)
):
    product_data = product.model_dump()
    # Convert Decimal to float for MongoDB storage
    product_data = convert_decimal_to_float(product_data)
    # Always derive is_active from stock_quantity
    product_data["is_active"] = product_data["stock_quantity"] > 0
    result = await products_collection.insert_one(product_data)
    return ProductResponse(id=str(result.inserted_id), **product_data)

# Get product by ID
@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str, 
    products_collection: AsyncIOMotorCollection = Depends(get_products_collection)
):
    # Validate ID format
    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid product ID format: {product_id}. Must be a 24-character hex string."
        )
    
    # Create ObjectId after validation
    object_id = ObjectId(product_id)
    
    # Find the product
    product_data = await products_collection.find_one({"_id": object_id})
    
    # Check if product exists
    if product_data is None:
        raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")
    
    try:
        # Use helper function to prepare data
        product_dict = prepare_product_data(product_data)
        product = Product(**product_dict)
        return ProductResponse(**product.model_dump(by_alias=False))
        
    except Exception as e:
        # Log the error
        print(f"Error in get_product: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# Get a paginated list of products with sorting and filtering
@router.get("/", response_model=PaginatedResponse[ProductResponse])
async def get_products(
    skip: int = Query(0, ge=0, description="Number of products to skip"),
    limit: int = Query(10, ge=1, le=100, description="Max number of products to return"),
    sort_by: Optional[str] = Query(None, description="Field to sort by (e.g., 'price', 'name')"),
    sort_order: int = Query(1, ge=-1, le=1, description="Sort order: 1 for ascending, -1 for descending"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, gt=0, description="Maximum price filter"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    products_collection: AsyncIOMotorCollection = Depends(get_products_collection)
):
    # Build filter query
    query = {}
    
    # Price range filter
    price_filter = {}
    if min_price is not None:
        price_filter["$gte"] = min_price
    if max_price is not None:
        price_filter["$lte"] = max_price
    if price_filter:
        query["price"] = price_filter
    
    # Category filter
    if category:
        query["category"] = category
    
    # Active status filter
    if is_active is not None:
        query["is_active"] = is_active
    
    # Text search
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    
    # Get total count for pagination metadata
    total_count = await products_collection.count_documents(query)
    
    # Build sort query
    sort_query = []
    if sort_by:
        sort_query.append((sort_by, sort_order))
    else:
        sort_query.append(("_id", 1))  # Default sort by ID
    
    # Get paginated products
    cursor = products_collection.find(query).sort(sort_query).skip(skip).limit(limit)
    products = await cursor.to_list(length=limit)
    
    # Convert to response models using helper function
    product_responses = [
        ProductResponse(**{k: v for k, v in prepare_product_data(product).items() if k != "_id"}, id=str(product["_id"]))
        for product in products
    ]
    
    # Return with pagination metadata
    return PaginatedResponse(
        items=product_responses,
        total=total_count,
        skip=skip,
        limit=limit,
        has_more=(skip + limit) < total_count
    )

# Delete a product
@router.delete("/{product_id}")
async def delete_product(
    product_id: str, 
    products_collection: AsyncIOMotorCollection = Depends(get_products_collection)
):
    # Validate ID format
    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid product ID format: {product_id}. Must be a 24-character hex string."
        )
    
    # Create ObjectId after validation
    object_id = ObjectId(product_id)
    
    # First check if the product exists
    product = await products_collection.find_one({"_id": object_id})
    if not product:
        raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")
        
    try:
        # Delete the product
        result = await products_collection.delete_one({"_id": object_id})
        
        if result.deleted_count == 0:
            # This should rarely happen since we already checked existence
            raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")
            
        return {"message": f"Product with ID {product_id} deleted successfully"}
        
    except Exception as e:
        # Log the error
        print(f"Error in delete_product: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# Update a product (full update)
@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product: ProductCreate,
    products_collection: AsyncIOMotorCollection = Depends(get_products_collection)
):
    # Validate ID format
    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid product ID format: {product_id}. Must be a 24-character hex string."
        )
    
    # Create ObjectId after validation
    object_id = ObjectId(product_id)
    
    # Check if product exists
    existing_product = await products_collection.find_one({"_id": object_id})
    if not existing_product:
        raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")
    
    try:
        # Update the product
        product_data = product.model_dump()
        # Convert Decimal to float for MongoDB storage
        product_data = convert_decimal_to_float(product_data)
        # Always derive is_active from stock_quantity
        product_data["is_active"] = product_data["stock_quantity"] > 0
        
        result = await products_collection.replace_one(
            {"_id": object_id}, 
            product_data
        )
        
        if result.modified_count == 0:
            # If no changes were made
            return ProductResponse(id=product_id, **product_data)
        
        # Get the updated product
        updated_product = await products_collection.find_one({"_id": object_id})
        product_dict = prepare_product_data(updated_product)
        return ProductResponse(**{k: v for k, v in product_dict.items() if k != "_id"}, id=product_dict["_id"])
        
    except Exception as e:
        # Log the error
        print(f"Error in update_product: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# Partially update a product
@router.patch("/{product_id}", response_model=ProductResponse)
async def patch_product(
    product_id: str,
    product_update: ProductUpdate,
    products_collection: AsyncIOMotorCollection = Depends(get_products_collection)
):
    # Validate ID format
    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid product ID format: {product_id}. Must be a 24-character hex string."
        )
    
    # Create ObjectId after validation
    object_id = ObjectId(product_id)
    
    # Check if product exists
    existing_product = await products_collection.find_one({"_id": object_id})
    if not existing_product:
        raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")
    
    try:
        # Get only the fields that were provided for the update
        update_data = {k: v for k, v in product_update.model_dump().items() if v is not None}
        
        if not update_data:
            # If no fields to update, return the existing product
            return ProductResponse(id=product_id, **{k: v for k, v in existing_product.items() if k != "_id"})
        
        # Convert Decimal to float for MongoDB storage
        update_data = convert_decimal_to_float(update_data)
        
        # If stock_quantity is being updated, update is_active accordingly
        if "stock_quantity" in update_data:
            update_data["is_active"] = update_data["stock_quantity"] > 0
        
        # Update the product with only the provided fields
        result = await products_collection.update_one(
            {"_id": object_id}, 
            {"$set": update_data}
        )
        
        # Get the updated product
        updated_product = await products_collection.find_one({"_id": object_id})
        product_dict = prepare_product_data(updated_product)
        
        # Ensure is_active is always based on stock_quantity
        product_dict["is_active"] = product_dict["stock_quantity"] > 0
        
        return ProductResponse(**{k: v for k, v in product_dict.items() if k != "_id"}, id=product_dict["_id"])
        
    except Exception as e:
        # Log the error
        print(f"Error in patch_product: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}") 