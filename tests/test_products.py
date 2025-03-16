import pytest
from fastapi.testclient import TestClient
from bson import ObjectId
from decimal import Decimal

# Test creating a new product
def test_create_product(client, sample_product_data):
    response = client.post("/products/", json=sample_product_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == sample_product_data["name"]
    assert data["description"] == sample_product_data["description"]
    assert float(data["price"]) == sample_product_data["price"]
    assert data["stock_quantity"] == sample_product_data["stock_quantity"]
    assert data["category"] == sample_product_data["category"]
    assert "id" in data
    assert data["is_active"] == True

# Test creating a product with invalid data
def test_create_product_invalid_data(client):
    # Test with short name
    response = client.post("/products/", json={
        "name": "A",
        "description": "This is a test product with a detailed description",
        "price": 19.99,
        "stock_quantity": 10
    })
    assert response.status_code == 422
    
    # Test with negative price
    response = client.post("/products/", json={
        "name": "Test Product",
        "description": "This is a test product with a detailed description",
        "price": -19.99,
        "stock_quantity": 10,
        "category": "Test Category"
    })
    assert response.status_code == 422
    
    # Test with negative stock
    response = client.post("/products/", json={
        "name": "Test Product",
        "description": "This is a test product with a detailed description",
        "price": 19.99,
        "stock_quantity": -10,
        "category": "Test Category"
    })
    assert response.status_code == 422

    response = client.post("/products/", json={
        "name": "Test Product",
        "description": "This is a",
        "price": 19.99,
        "stock_quantity": 10,
        "category": "Test Category"
    })
    assert response.status_code == 422
    
    # Test with missing fields
    response = client.post("/products/", json={
        "name": "Test Product",
        "price": 19.99
    })
    assert response.status_code == 422

# Test getting a product by ID
def test_get_product_by_id(client, create_test_product):
    product = create_test_product
    product_id = product["id"]
    
    response = client.get(f"/products/{product_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == product_id
    assert data["name"] == product["name"]
    assert data["description"] == product["description"]
    assert data["price"] == product["price"]
    assert data["stock_quantity"] == product["stock_quantity"]
    assert data["category"] == product["category"]
    assert data["is_active"] == product["is_active"]

# Test getting a non-existent product
def test_get_nonexistent_product(client):
    fake_id = str(ObjectId('99999461e07461e074619999'))
    response = client.get(f"/products/{fake_id}")
    
    assert response.status_code == 404

# Test getting a product with invalid ID format
def test_get_product_invalid_id(client):
    response1 = client.get("/products/66e074")
    response2 = client.get("/products/123456")
    response3 = client.get("/products/------")
    response4 = client.get("/products/2034982304982304982304982304982304982304")
    
    assert response1.status_code == 400
    assert response2.status_code == 400
    assert response3.status_code == 400
    assert response4.status_code == 400

# Test updating a product
def test_update_product(client, create_test_product):
    product = create_test_product
    product_id = product["id"]
    
    update_data = {
        "name": "Updated Product",
        "description": "This is an updated test product with a detailed description",
        "price": 29.99,
        "stock_quantity": 15,
        "category": "Updated Category"
    }
    
    response = client.put(f"/products/{product_id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == product_id
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]
    assert float(data["price"]) == update_data["price"]
    assert data["stock_quantity"] == update_data["stock_quantity"]
    assert data["category"] == update_data["category"]
    assert data["is_active"] == True

# Test updating a product with invalid data
def test_update_product_invalid_data(client, create_test_product):
    product = create_test_product
    product_id = product["id"]
    
    
    response1 = client.put(f"/products/{product_id}", json={
        "name": "Updated Product",
        "description": "This is a",
        "price": 19.99,
        "stock_quantity": 10,
        "category": "Test Category"
    })
    
    assert response1.status_code == 422  

    response2 = client.put(f"/products/{product_id}", json={
        "name": "Updated Product",
        "price": 19.99
    })
    assert response2.status_code == 422
    
    response3 = client.put(f"/products/{product_id}", json={
        "name": "Updated Product",
        "price": 19.99,
        "stock_quantity": 10,
        "category": "Test Category"
    })
    assert response3.status_code == 422

    response4 = client.put(f"/products/{product_id}", json={
        "name": "Updated Product",
        "price": -19.99,
        "stock_quantity": 10,
        "category": "Test Category"
    })
    assert response4.status_code == 422

# Test partially updating a product
def test_patch_product(client, create_test_product):
    product = create_test_product
    product_id = product["id"]
    
    # Update only the price and stock
    update_data = {
        "price": 39.99,
        "stock_quantity": 5
    }
    
    response = client.patch(f"/products/{product_id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == product_id
    assert data["name"] == product["name"]  # Name should remain unchanged
    assert data["description"] == product["description"]  # Description should remain unchanged
    assert float(data["price"]) == update_data["price"]
    assert data["stock_quantity"] == update_data["stock_quantity"]  # Stock should be updated
    assert data["category"] == product["category"]  # Category should remain unchanged
    assert data["is_active"] == True

# Test partially updating a product with invalid data
def test_patch_product_invalid_data(client, create_test_product):
    product = create_test_product
    product_id = product["id"]
    
    response1 = client.patch(f"/products/{product_id}", json={
        "price": -19.99,
        "stock_quantity": 10,
        "category": "Test Category"
    })
    assert response1.status_code == 422

    response2 = client.patch(f"/products/{product_id}", json={
        "price": 19.99,
        "stock_quantity": -10,
        "category": "Test Category"
    })
    assert response2.status_code == 422

    response3 = client.patch(f"/products/{product_id}", json={
        "name": "Updated Product",
        "description": "This is a",
        "price": 19.99,
        "stock_quantity": 10,
        "category": "Test Category"
    })
    assert response3.status_code == 422

    response4 = client.patch(f"/products/{product_id}", json={
        "name": "Updated Product",
        "description": "This is a test product with a detailed description",
        "stock_quantity": 10,
        "category": 123
    })
    assert response4.status_code == 422

# Test product becomes inactive when stock reaches zero
def test_product_inactive_when_stock_zero(client, create_test_product, create_test_user):
    product = create_test_product
    user = create_test_user
    cart_id = user["cart_id"]
    
    # Add all available stock to cart
    item_data = {
        "product_id": product["id"],
        "quantity": product["stock_quantity"]
    }
    
    response = client.post(f"/carts/{cart_id}/items", json=item_data)
    assert response.status_code == 200
    
    # Check that product is now inactive
    product_response = client.get(f"/products/{product['id']}")
    assert product_response.status_code == 200
    updated_product = product_response.json()
    assert updated_product["stock_quantity"] == 0
    assert updated_product["is_active"] == False

# Test product becomes active again when stock is restored
def test_product_active_when_stock_restored(client, create_test_product, create_test_user):
    product = create_test_product
    user = create_test_user
    cart_id = user["cart_id"]
    
    # First add all stock to make product inactive
    item_data = {
        "product_id": product["id"],
        "quantity": product["stock_quantity"]
    }
    
    client.post(f"/carts/{cart_id}/items", json=item_data)
    
    # Verify product is inactive
    product_response = client.get(f"/products/{product['id']}")
    updated_product = product_response.json()
    assert updated_product["is_active"] == False
    
    # Now remove the item from cart to restore stock
    response = client.delete(f"/carts/{cart_id}/items/{product['id']}")
    assert response.status_code == 200
    
    # Check that product is active again
    product_response = client.get(f"/products/{product['id']}")
    assert product_response.status_code == 200
    restored_product = product_response.json()
    assert restored_product["stock_quantity"] > 0
    assert restored_product["is_active"] == True

# Test updating product stock directly
def test_update_product_stock(client, create_test_product):
    product = create_test_product
    product_id = product["id"]
    
    # Update the product with new stock
    update_data = {
        "stock_quantity": 20
    }
    
    response = client.patch(f"/products/{product_id}", json=update_data)
    assert response.status_code == 200
    updated_product = response.json()
    assert updated_product["stock_quantity"] == 20

# Test deleting a product
def test_delete_product(client, create_test_product):
    product = create_test_product
    product_id = product["id"]
    
    response = client.delete(f"/products/{product_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert f"Product with ID {product_id} deleted successfully" in data["message"]
    
    # Verify the product is actually deleted
    get_response = client.get(f"/products/{product_id}")
    assert get_response.status_code == 404

# Test getting all products
def test_get_all_products(client):
    # Create multiple products
    categories = ["Electronics", "Books", "Clothing"]
    prices = [9.99, 19.99, 29.99, 39.99, 49.99]
    
    for i in range(5):
        client.post("/products/", json={
            "name": f"Test Product {i}",
            "description": f"This is test product {i} with a detailed description",
            "price": prices[i],
            "stock_quantity": 10 * (i + 1),
            "category": categories[i % len(categories)]
        })
    
    response = client.get("/products/")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check if it's a paginated response
    if isinstance(data, dict) and "items" in data:
        # Paginated response
        assert "items" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        
        # Verify we have at least 5 products
        assert len(data["items"]) >= 5
        
        # Verify the structure of each product
        for product in data["items"]:
            assert "id" in product
            assert "name" in product
            assert "description" in product
            assert "price" in product
            assert "stock_quantity" in product
            assert "category" in product
            assert "is_active" in product
    else:
        # Non-paginated response (simple list)
        assert isinstance(data, list)
        assert len(data) >= 5
        
        # Verify the structure of each product
        for product in data:
            assert "id" in product
            assert "name" in product
            assert "description" in product
            assert "price" in product
            assert "stock_quantity" in product
            assert "category" in product
            assert "is_active" in product 