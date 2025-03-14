from fastapi import APIRouter, HTTPException, Depends, Path, Query
from bson import ObjectId
from bson.errors import InvalidId
from database import get_users_collection
from models.user import UserCreate, UserResponse, User, PaginatedResponse
from motor.motor_asyncio import AsyncIOMotorCollection

router = APIRouter()

# Create a new user
@router.post("/users", response_model=UserResponse)
async def create_user(user: UserCreate, users_collection: AsyncIOMotorCollection = Depends(get_users_collection)):
    user_data = user.model_dump()
    result = await users_collection.insert_one(user_data)
    return UserResponse(id=str(result.inserted_id), **user_data)

# Get all users
@router.get("/users", response_model=PaginatedResponse[UserResponse])
async def get_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(10, ge=1, le=100, description="Max number of users to return"),
    users_collection: AsyncIOMotorCollection = Depends(get_users_collection)
):
    # Get total count for pagination metadata
    total_count = await users_collection.count_documents({})
    
    # Get paginated users
    users = await users_collection.find().skip(skip).limit(limit).to_list(length=limit)
    
    # Convert to response models
    user_responses = [
        UserResponse(id=str(user["_id"]), name=user["name"], email=user["email"]) 
        for user in users
    ]
    
    # Return with pagination metadata
    return PaginatedResponse(
        items=user_responses,
        total=total_count,
        skip=skip,
        limit=limit,
        has_more=(skip + limit) < total_count
    )

# Get a user by ID
@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, users_collection: AsyncIOMotorCollection = Depends(get_users_collection)):
    # First validate the ID format before any database operations
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid user ID format: {user_id}. Must be a 24-character hex string."
        )
    
    # Create ObjectId after validation
    object_id = ObjectId(user_id)
    
    # Find the user
    user_data = await users_collection.find_one({"_id": object_id})
    
    # Check if user exists - do this outside the try/except block
    if user_data is None:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")
    
    try:
        # Use User model to validate database document
        user = User(_id=str(user_data["_id"]), name=user_data["name"], email=user_data["email"])
        
        # Convert to response model
        return UserResponse(**user.model_dump(by_alias=False))
        
    except Exception as e:
        # Log the error
        print(f"Error in get_user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# Delete a user by ID
@router.delete("/users/{user_id}")
async def delete_user(user_id: str, users_collection: AsyncIOMotorCollection = Depends(get_users_collection)):
    # First validate the ID format before any database operations
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid user ID format: {user_id}. Must be a 24-character hex string."
        )
    
    # Create ObjectId after validation
    object_id = ObjectId(user_id)
    
    # First check if the user exists
    user = await users_collection.find_one({"_id": object_id})
    if not user:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")
        
    try:
        # Delete the user
        result = await users_collection.delete_one({"_id": object_id})
        
        if result.deleted_count == 0:
            # This should rarely happen since we already checked existence
            raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")
            
        return {"message": f"User with ID {user_id} deleted successfully"}
        
    except Exception as e:
        # Log the error
        print(f"Error in delete_user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}") 