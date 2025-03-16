import pytest
from fastapi.testclient import TestClient
from bson import ObjectId

# Test creating a new user
def test_create_user(client, sample_user_data):
    response = client.post("/users/", json=sample_user_data)
    
    assert response.status_code == 200
    user = response.json()
    assert "id" in user
    assert user["name"] == sample_user_data["name"]
    assert user["email"] == sample_user_data["email"]
    
    # Verify cart_id is included and not None
    assert "cart_id" in user
    assert user["cart_id"] is not None
    
    # Verify the cart exists and is associated with the user
    cart_response = client.get(f"/carts/{user['cart_id']}")
    assert cart_response.status_code == 200
    cart = cart_response.json()
    assert cart["user_id"] == user["id"]
    assert cart["items"] == []

# Test creating a user with invalid data
def test_create_user_invalid_data(client):
    # Test with short name
    response = client.post("/users/", json={"name": "A", "email": "test@example.com"})
    assert response.status_code == 422
    
    # Test with invalid email
    response = client.post("/users/", json={"name": "Test User", "email": "invalid-email"})
    assert response.status_code == 422
    
    # Test with missing fields
    response = client.post("/users/", json={"name": "Test User"})
    assert response.status_code == 422

# Test getting a user by ID
def test_get_user_by_id(client, create_test_user):
    user = create_test_user
    user_id = user["id"]
    
    response = client.get(f"/users/{user_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["name"] == user["name"]
    assert data["email"] == user["email"]
    assert "cart_id" in data

# Test getting a non-existent user
def test_get_nonexistent_user(client):
    fake_id = str(ObjectId('66e07461e07461e07461e074'))
    response = client.get(f"/users/{fake_id}")
    
    assert response.status_code == 404

# Test getting a user with invalid ID format
def test_get_user_invalid_id(client):
    response1 = client.get("/users/66e074")
    response2 = client.get("/users/123456")
    response3 = client.get("/users/------")
    response4 = client.get("/users/2034982304982304982304982304982304982304")
    
    assert response1.status_code == 400
    assert response2.status_code == 400
    assert response3.status_code == 400
    assert response4.status_code == 400 

# Test updating a user
def test_update_user(client, create_test_user):
    user = create_test_user
    user_id = user["id"]
    
    update_data = {
        "name": "Updated User",
        "email": "updated@example.com"
    }
    
    response = client.put(f"/users/{user_id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["name"] == update_data["name"]
    assert data["email"] == update_data["email"]
    assert "cart_id" in data

# Test partially updating a user
def test_patch_user(client, create_test_user):
    user = create_test_user
    user_id = user["id"]
    
    # Update only the name
    update_data = {
        "name": "Partially Updated User"
    }
    
    response = client.patch(f"/users/{user_id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["name"] == update_data["name"]
    assert data["email"] == user["email"]  # Email should remain unchanged
    assert "cart_id" in data

# Test deleting a user
def test_delete_user(client, create_test_user):
    user = create_test_user
    user_id = user["id"]
    
    response = client.delete(f"/users/{user_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert f"User with ID {user_id} deleted successfully" in data["message"]
    
    # Verify the user is actually deleted
    get_response = client.get(f"/users/{user_id}")
    assert get_response.status_code == 404

# Test getting all users
def test_get_all_users(client):
    # Create multiple users
    for i in range(5):
        client.post("/users/", json={
            "name": f"Test User {i}",
            "email": f"test{i}@example.com"
        })
    
    response = client.get("/users/")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check if it's a paginated response
    assert "items" in data
    assert "total" in data
    assert "skip" in data
    assert "limit" in data
    assert "has_more" in data
    
    # Verify we have at least 5 users
    assert len(data["items"]) >= 5
    
    # Verify the structure of each user
    for user in data["items"]:
        assert "id" in user
        assert "name" in user
        assert "email" in user
        assert "cart_id" in user 

# Test that cart_id is included in user responses
def test_get_user_includes_cart_id(client, create_test_user):
    user = create_test_user
    user_id = user["id"]
    
    response = client.get(f"/users/{user_id}")
    
    assert response.status_code == 200
    user_data = response.json()
    assert "cart_id" in user_data
    assert user_data["cart_id"] is not None
    assert user_data["cart_id"] == user["cart_id"]

# Test that cart_id is included in list users response
def test_list_users_includes_cart_id(client, create_test_user):
    response = client.get("/users/")
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0
    
    # Check that at least one user has a cart_id
    user_with_cart = False
    for user in data["items"]:
        if "cart_id" in user and user["cart_id"] is not None:
            user_with_cart = True
            break
    
    assert user_with_cart, "No users with cart_id found in the response" 