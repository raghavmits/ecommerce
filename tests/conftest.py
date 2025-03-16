import pytest
import sys
import os
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

# Add the crush-mongo directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now import directly from the modules
from main import app
from database import client as app_client, database as app_database

# Test database name
TEST_DB_NAME = "test_bookstore"

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db():
    """Set up the test database before each test."""
    # Create a mock client
    client = AsyncMongoMockClient()
    
    # Store original database connections
    original_client = app_client
    original_database = app_database
    
    # Override the app's database connection with our test database
    import database
    database.client = client
    database.database = client[TEST_DB_NAME]
    
    yield
    
    # Restore original database connection
    import database
    database.client = original_client
    database.database = original_database

# Test data fixtures
@pytest.fixture
def sample_user_data():
    return {
        "name": "Test User",
        "email": "test@example.com"
    }

@pytest.fixture
def sample_product_data():
    return {
        "name": "Test Product",
        "description": "This is a test product with a detailed description",
        "price": 19.99,
        "stock_quantity": 10,
        "category": "Test Category"
    }

@pytest.fixture
def create_test_user(client, sample_user_data):
    """Create a test user and return the user data."""
    response = client.post("/users/", json=sample_user_data)
    return response.json()

@pytest.fixture
def create_test_product(client, sample_product_data):
    """Create a test product and return the product data."""
    response = client.post("/products/", json=sample_product_data)
    return response.json()

@pytest.fixture
def create_test_cart_with_items(client, create_test_user, create_test_product):
    """Create a test cart with items and return the cart data."""
    user = create_test_user
    product = create_test_product
    
    # The cart should already be created with the user
    cart_id = user["cart_id"]
    
    # Add an item to the cart
    item_data = {
        "product_id": product["id"],
        "quantity": 2
    }
    response = client.post(f"/carts/{cart_id}/items", json=item_data)
    return response.json()

@pytest.fixture
def get_user_from_db():
    """Get a user directly from the database."""
    async def _get_user(user_id):
        from bson import ObjectId
        from motor.motor_asyncio import AsyncIOMotorClient
        
        # Use the same connection string as your API
        client = AsyncIOMotorClient("***REMOVED***")
        db = client["bookstore"]
        users_collection = db["users"]
        
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
        return user
    
    return _get_user 

