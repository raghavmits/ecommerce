import pytest
from fastapi.testclient import TestClient
from bson import ObjectId
import asyncio

# Test that a cart is created automatically when a user is created
def test_cart_created_with_user(client, sample_user_data):
    response = client.post("/users/", json=sample_user_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "cart_id" in data
    assert data["cart_id"] is not None
    
    # Verify the cart exists and is associated with the user
    cart_id = data["cart_id"]
    response = client.get(f"/carts/{cart_id}")
    
    assert response.status_code == 200
    cart_data = response.json()
    assert cart_data["id"] == cart_id
    assert cart_data["user_id"] == data["id"]
    assert cart_data["items"] == []

# Test getting a cart by ID
def test_get_cart_by_id(client, create_test_user):
    user = create_test_user
    cart_id = user["cart_id"]
    
    response = client.get(f"/carts/{cart_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == cart_id
    assert data["user_id"] == user["id"]
    assert "items" in data
    assert isinstance(data["items"], list)

# Test getting a non-existent cart
def test_get_nonexistent_cart(client):
    fake_id = str(ObjectId('99999461e07461e074699999'))
    response = client.get(f"/carts/{fake_id}")
    
    assert response.status_code == 404

# Test getting a cart with invalid ID format
def test_get_cart_invalid_id(client):
    response1 = client.get("/carts/66e074")
    response2 = client.get("/carts/123456")
    response3 = client.get("/carts/------")
    response4 = client.get("/carts/2034982304982304982304982304982304982304")   
    
    assert response1.status_code == 400
    assert response2.status_code == 400
    assert response3.status_code == 400
    assert response4.status_code == 400

# Test adding an item to a cart
def test_add_item_to_cart(client, create_test_user, create_test_product):
    user = create_test_user
    product = create_test_product
    cart_id = user["cart_id"]
    
    item_data = {
        "product_id": product["id"],
        "quantity": 2
    }
    
    response = client.post(f"/carts/{cart_id}/items", json=item_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == cart_id
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == product["id"]
    assert data["items"][0]["quantity"] == 2

# Test adding an item with invalid quantity
def test_add_item_invalid_quantity(client, create_test_user, create_test_product):
    user = create_test_user
    product = create_test_product
    cart_id = user["cart_id"]
    
    # Try to add with zero quantity
    item_data = {
        "product_id": product["id"],
        "quantity": 0
    }
    
    response = client.post(f"/carts/{cart_id}/items", json=item_data)
    assert response.status_code == 422
    
    # Try to add with negative quantity
    item_data = {
        "product_id": product["id"],
        "quantity": -1
    }
    
    response = client.post(f"/carts/{cart_id}/items", json=item_data)
    assert response.status_code == 422

# Test adding more quantity of an existing item
def test_add_more_of_existing_item(client, create_test_user, create_test_product):
    user = create_test_user
    product = create_test_product
    cart_id = user["cart_id"]
    
    # Add initial quantity
    item_data = {
        "product_id": product["id"],
        "quantity": 2
    }
    
    client.post(f"/carts/{cart_id}/items", json=item_data)
    
    # Add more of the same product
    item_data = {
        "product_id": product["id"],
        "quantity": 3
    }
    
    response = client.post(f"/carts/{cart_id}/items", json=item_data)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1  # Still only one item type
    assert data["items"][0]["product_id"] == product["id"]
    assert data["items"][0]["quantity"] == 5  # 2 + 3 = 5

# Test adding an item that exceeds available stock
def test_add_item_exceeds_stock(client, create_test_user, create_test_product):
    user = create_test_user
    product = create_test_product
    cart_id = user["cart_id"]
    
    # Try to add more than available stock
    item_data = {
        "product_id": product["id"],
        "quantity": product["stock_quantity"] + 1
    }
    
    response = client.post(f"/carts/{cart_id}/items", json=item_data)
    assert response.status_code == 400

# Test updating item quantity in cart
def test_update_item_quantity(client, create_test_cart_with_items):
    cart = create_test_cart_with_items
    cart_id = cart["id"]
    product_id = cart["items"][0]["product_id"]
    
    update_data = {
        "quantity": 4
    }
    
    response = client.put(f"/carts/{cart_id}/items/{product_id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == cart_id
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == product_id
    assert data["items"][0]["quantity"] == 4

# Test removing an item from a cart
def test_remove_item_from_cart(client, create_test_cart_with_items):
    cart = create_test_cart_with_items
    cart_id = cart["id"]
    product_id = cart["items"][0]["product_id"]
    
    response = client.delete(f"/carts/{cart_id}/items/{product_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == cart_id
    assert len(data["items"]) == 0

# Test clearing a cart
def test_clear_cart(client, create_test_cart_with_items):
    cart = create_test_cart_with_items
    cart_id = cart["id"]
    
    response = client.delete(f"/carts/{cart_id}/items")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == cart_id
    assert len(data["items"]) == 0

# Test deleting a cart
def test_delete_cart(client, create_test_cart_with_items):
    # Get the test cart with items
    cart = create_test_cart_with_items
    cart_id = cart["id"]
    
    # Get the initial product stock
    product_id = cart["items"][0]["product_id"]
    initial_product = client.get(f"/products/{product_id}").json()
    initial_stock = initial_product["stock_quantity"]
    
    # Get the user associated with the cart
    user_id = cart["user_id"]
    initial_user = client.get(f"/users/{user_id}").json()
    
    # Delete (checkout) the cart
    response = client.delete(f"/carts/{cart_id}")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "checked out successfully" in data["message"]
    assert "new_cart_id" in data
    new_cart_id = data["new_cart_id"]
    
    # Verify the old cart is deleted
    old_cart_response = client.get(f"/carts/{cart_id}")
    assert old_cart_response.status_code == 404
    
    # Verify a new cart was created and is empty
    new_cart_response = client.get(f"/carts/{new_cart_id}")
    assert new_cart_response.status_code == 200
    new_cart = new_cart_response.json()
    assert new_cart["id"] == new_cart_id
    assert new_cart["user_id"] == user_id
    assert new_cart["items"] == []
    
    # Verify the user now has the new cart ID through the API
    updated_user_response = client.get(f"/users/{user_id}")
    assert updated_user_response.status_code == 200
    updated_user = updated_user_response.json()
    assert updated_user["cart_id"] == new_cart_id
    
    # Verify the product stock was reduced
    updated_product = client.get(f"/products/{product_id}").json()
    item_quantity = cart["items"][0]["quantity"]
    assert updated_product["stock_quantity"] == initial_stock - item_quantity
    
    # If the product is now out of stock, verify it's marked as inactive
    if updated_product["stock_quantity"] == 0:
        assert updated_product["is_active"] == False

# Test adding multiple different items to a cart
def test_add_multiple_items(client, create_test_user):
    user = create_test_user
    cart_id = user["cart_id"]
    
    # Create multiple products
    products = []
    for i in range(3):
        product_data = {
            "name": f"Test Product {i}",
            "description": f"This is test product {i} with a detailed description",
            "price": 10.99 + i,
            "stock_quantity": 10,
            "category": "Test"
        }
        response = client.post("/products/", json=product_data)
        products.append(response.json())
    
    # Add each product to the cart
    for i, product in enumerate(products):
        item_data = {
            "product_id": product["id"],
            "quantity": i + 1
        }
        client.post(f"/carts/{cart_id}/items", json=item_data)
    
    # Get the cart and verify all items are there
    response = client.get(f"/carts/{cart_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3
    
    # Verify each item has the correct quantity
    for i, item in enumerate(data["items"]):
        assert item["product_id"] in [p["id"] for p in products]
        product_index = next(idx for idx, p in enumerate(products) if p["id"] == item["product_id"])
        assert item["quantity"] == product_index + 1

# Test stock decreases when item is added to cart
def test_stock_decreases_when_item_added(client, create_test_product, create_test_user):
    product = create_test_product
    initial_stock = product["stock_quantity"]
    user = create_test_user
    cart_id = user["cart_id"]
    
    # Add item to cart
    item_data = {
        "product_id": product["id"],
        "quantity": 2
    }
    
    response = client.post(f"/carts/{cart_id}/items", json=item_data)
    assert response.status_code == 200
    
    # Check that product stock has decreased
    product_response = client.get(f"/products/{product['id']}")
    assert product_response.status_code == 200
    updated_product = product_response.json()
    assert updated_product["stock_quantity"] == initial_stock - 2

# Test stock increases when item is removed from cart
def test_stock_increases_when_item_removed(client, create_test_cart_with_items):
    cart = create_test_cart_with_items
    cart_id = cart["id"]
    product_id = cart["items"][0]["product_id"]
    quantity = cart["items"][0]["quantity"]
    
    # Get initial product stock
    product_response = client.get(f"/products/{product_id}")
    initial_stock = product_response.json()["stock_quantity"]
    
    # Remove item from cart
    response = client.delete(f"/carts/{cart_id}/items/{product_id}")
    assert response.status_code == 200
    
    # Check that product stock has increased
    product_response = client.get(f"/products/{product_id}")
    assert product_response.status_code == 200
    updated_product = product_response.json()
    assert updated_product["stock_quantity"] == initial_stock + quantity

# Test validation against available stock
def test_validation_against_available_stock(client, create_test_product, create_test_user):
    product = create_test_product
    available_stock = product["stock_quantity"]
    user = create_test_user
    cart_id = user["cart_id"]
    
    # Try to add more than available stock
    item_data = {
        "product_id": product["id"],
        "quantity": available_stock + 1
    }
    
    response = client.post(f"/carts/{cart_id}/items", json=item_data)
    assert response.status_code == 400
    assert "Not enough stock" in response.json()["detail"]
    
    # Add valid quantity
    item_data["quantity"] = available_stock
    response = client.post(f"/carts/{cart_id}/items", json=item_data)
    assert response.status_code == 200
    
    # Try to add more (should fail as no stock left)
    item_data["quantity"] = 1
    response = client.post(f"/carts/{cart_id}/items", json=item_data)
    assert response.status_code == 400
    assert "is not available" in response.json()["detail"]

# Test updating cart item quantity validates against available stock
def test_update_quantity_validates_stock(client, create_test_cart_with_items):
    cart = create_test_cart_with_items
    cart_id = cart["id"]
    product_id = cart["items"][0]["product_id"]
    
    # Get product to check available stock
    product_response = client.get(f"/products/{product_id}")
    product = product_response.json()
    available_stock = product["stock_quantity"]
    current_cart_quantity = cart["items"][0]["quantity"]
    
    # Try to update to more than available stock
    update_data = {
        "quantity": current_cart_quantity + available_stock + 1
    }
    
    response = client.put(f"/carts/{cart_id}/items/{product_id}", json=update_data)
    assert response.status_code == 400
    assert "Not enough stock" in response.json()["detail"]
    
    # Update to valid quantity
    update_data["quantity"] = current_cart_quantity + available_stock
    response = client.put(f"/carts/{cart_id}/items/{product_id}", json=update_data)
    assert response.status_code == 200

# Test complete checkout process
def test_complete_checkout_process(client, create_test_user):
    user = create_test_user
    user_id = user["id"]
    cart_id = user["cart_id"]
    
    # Create multiple products
    products = []
    for i in range(3):
        product_data = {
            "name": f"Checkout Product {i}",
            "description": f"Product for checkout test {i}",
            "price": 10.99 + i,
            "stock_quantity": 10,
            "category": "Test"
        }
        response = client.post("/products/", json=product_data)
        products.append(response.json())
    
    # Add different quantities of each product to cart
    for i, product in enumerate(products):
        item_data = {
            "product_id": product["id"],
            "quantity": i + 1
        }
        client.post(f"/carts/{cart_id}/items", json=item_data)
    
    # Record initial stock levels
    initial_stocks = {}
    for product in products:
        product_response = client.get(f"/products/{product['id']}")
        initial_stocks[product["id"]] = product_response.json()["stock_quantity"]
    
    # Checkout (delete cart)
    response = client.delete(f"/carts/{cart_id}")
    assert response.status_code == 200
    data = response.json()
    assert "new_cart_id" in data
    new_cart_id = data["new_cart_id"]
    
    # Verify old cart is gone
    old_cart_response = client.get(f"/carts/{cart_id}")
    assert old_cart_response.status_code == 404
    
    # Verify new cart exists and is empty
    new_cart_response = client.get(f"/carts/{new_cart_id}")
    assert new_cart_response.status_code == 200
    new_cart = new_cart_response.json()
    assert new_cart["items"] == []
    
    # Verify user has new cart
    user_response = client.get(f"/users/{user_id}")
    assert user_response.status_code == 200
    updated_user = user_response.json()
    assert updated_user["cart_id"] == new_cart_id
    
    # Verify all products have reduced stock
    for i, product in enumerate(products):
        product_response = client.get(f"/products/{product['id']}")
        updated_product = product_response.json()
        expected_stock = initial_stocks[product["id"]] - (i + 1)
        assert updated_product["stock_quantity"] == expected_stock
        
        # Check if product should be inactive
        if expected_stock == 0:
            assert updated_product["is_active"] == False
        else:
            assert updated_product["is_active"] == True