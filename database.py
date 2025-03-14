# database.py
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from fastapi import Depends

MONGO_URI = "***REMOVED***"
DB_NAME = "user_db"

# Create a database connection
client = AsyncIOMotorClient(MONGO_URI)
database = client[DB_NAME]

# Dependency to get the database
async def get_database() -> AsyncIOMotorDatabase:
    return database

# Dependency to get the users collection
### Can add a dependency chain to get the database and then the users collection
async def get_users_collection(database: AsyncIOMotorDatabase = Depends(get_database)):
    return database.get_collection("users")


