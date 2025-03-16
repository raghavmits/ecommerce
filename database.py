# database.py
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from fastapi import Depends
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

# Create a database connection
client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
database = client[os.getenv("DB_NAME")]

# Dependency to get the database
async def get_database() -> AsyncIOMotorDatabase:
    return database

# Dependency to get the users collection
### Can add a dependency chain to get the database and then the users collection
async def get_users_collection(database: AsyncIOMotorDatabase = Depends(get_database)):
    return database.get_collection("users")

async def get_products_collection(database: AsyncIOMotorDatabase = Depends(get_database)):
    return database.get_collection("products")

async def get_carts_collection(database: AsyncIOMotorDatabase = Depends(get_database)):
    return database.get_collection("carts")

# Create indexes for better query performance
async def create_indexes():
    # Users collection indexes
    await database.users.create_index("email", unique=True)
    await database.users.create_index("cart_id")
    
    # Products collection indexes
    await database.products.create_index("name")
    await database.products.create_index("category")
    await database.products.create_index("price")
    await database.products.create_index("is_active")
    # Compound index for filtering products by category and price
    await database.products.create_index([("category", 1), ("price", 1)])
    # Text index for search functionality
    await database.products.create_index([("name", "text"), ("description", "text")])
    
    # Carts collection indexes
    await database.carts.create_index("user_id", unique=True)
    # Index for finding items in carts
    await database.carts.create_index("items.product_id")

    print("Database indexes created successfully")


