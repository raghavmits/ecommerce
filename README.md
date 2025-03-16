# E-Commerce Book Store Backend

An e-commerce backend API built with FastAPI and MongoDB, designed to provide a simple online shopping experience.

## 1. Project Overview

This e-commerce backend provides a simple API for managing an online book store. It handles users, products, and shopping carts with a focus on simplicity and ease of use.

### Key Features

- **User Management**: Create, read, update, and delete user accounts
- **Product Catalog**: Manage products with categories, pricing, and inventory
- **Shopping Cart**: Add, update, and remove items from carts
- **Inventory Management**: Automatic stock tracking and product availability
- **Checkout Process**: Complete purchase flow with inventory updates

The API is built using FastAPI for performance and MongoDB for flexible data storage, all containerized with Docker for easy deployment.

## 2. Setup Instructions

### Prerequisites

- Docker installed on your system
- Git (to clone the repository)

### Installation Steps

i. Clone the repository:
   ```bash
   git clone https://github.com/raghavmits/ecommerce.git
   cd <path-to-the-project>
   ```

ii. Change the `.env.example` file to `.env` and update the following variables with the right credentials:
   ```
   MONGO_URI=mongodb+srv://<username>:<password>@<cluster-url>/?retryWrites=true&w=majority
   DB_NAME=<database-name>
   ```

iii. Build and start the services:
   ```bash
   docker compose up
   ```

   This command will:
   - Build the Docker image for the API
   - Start the FastAPI application on port 8000
   - Connect to the MongoDB database specified in your `.env` file

iv. The API will be available at `http://localhost:8000`

## 3. API Documentation

FastAPI automatically generates comprehensive API documentation based on the code and docstrings.

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)


## 4. Key Assumptions & Design Decisions

### Database Structure

The application uses MongoDB with the following collections:

- **users**: Stores user information and references to their shopping carts
- **products**: Contains product details, pricing, and inventory information
- **carts**: Manages shopping carts with items and quantities

### Database Indexes

The application automatically creates the following indexes for better performance:

- **Users Collection**:
  - `email`: Unique index for fast user lookup and to ensure email uniqueness
  - `cart_id`: For quick access to user's cart information

- **Products Collection**:
  - `name`: For quick product lookup by name
  - `category`: For filtering products by category
  - `price`: For sorting and filtering by price
  - `is_active`: For filtering active/inactive products
  - Compound index on `(category, price)`: For efficient category+price filtering
  - Text index on `name` and `description`: For full-text search capabilities

- **Carts Collection**:
  - `user_id`: Unique index to ensure one cart per user
  - `items.product_id`: For quickly finding carts containing specific products

### Data Models

#### User Model

```python
class UserBase(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr

class User(UserBase):
    id: str
    cart_id: Optional[str] = None   
```

#### Product Model

```python
class ProductBase(BaseModel):
    name: str = Field(..., min_length=2)
    description: str = Field(..., min_length=10)
    price: Decimal = Field(..., gt=0)
    stock_quantity: int = Field(..., ge=0)
    category: Optional[str] = None

    @computed_field
    @property
    def is_active(self) -> bool:
        return self.stock_quantity > 0

class Product(ProductBase):
    id: str
```

#### Cart Model

```python
class CartItem(BaseModel):
    product_id: str
    quantity: int = Field(..., ge=1)

class Cart(BaseModel):
    id: str
    user_id: str
    items: List[CartItem] = []
```

### Key Design Decisions

1. **Automatic Cart Creation**: A shopping cart is automatically created when a user is registered
2. **Real-time Inventory Management**: Product stock is updated in real-time when items are added to or removed from carts
3. **Product Availability**: Products are automatically marked as inactive when stock reaches zero
4. **Checkout Process**: When a cart is checked out, the cart is deleted, stock is updated and a new empty cart is created for the user. Therefore the user always has a cart assigned to them.

### Optimizations

1. **Pagination**: All list endpoints support pagination for better performance with large datasets
2. **Filtering and Sorting**: Product listing supports filtering by various attributes and custom sorting
3. **Indexing**: The application automatically creates indexes for better search and retrieval performance
4. **Asynchronous Operations**: All database operations are asynchronous for better performance

## 5. Running Unit Tests

The project includes comprehensive unit tests for all endpoints and business logic.

### Running Tests in Docker

To run the tests inside the Docker container:

```bash
docker exec -it <container_name> pytest -v
```
Note: The container name is `ecommapi-api-1` if you are using the default configuration.

### Testing Framework

- **pytest**: Main testing framework
- **mongomock-motor**: For mocking MongoDB in tests
- **TestClient**: FastAPI's test client for API testing

The tests cover all API endpoints and business logic, ensuring the application works as expected.

## 6. Project Structure

```
ecommAPI/
├── .env                  # Environment variables
├── Dockerfile           # Docker configuration
├── docker-compose.yml   # Docker Compose configuration
├── requirements.txt     # Python dependencies
├── main.py              # FastAPI entry point
├── database.py          # Database connection
├── models/              # Pydantic models
│   ├── user.py
│   ├── product.py
│   ├── cart.py
│   └── common.py
├── routes/              # API routes
│   ├── users.py
│   ├── products.py
│   └── carts.py
└── tests/               # Unit tests
    ├── conftest.py
    ├── test_users.py
    ├── test_products.py
    └── test_carts.py
```


---

This README provides a comprehensive guide to setting up, using, and understanding the e-commerce backend API. For any questions or issues, please reach out to me at raghavmittal.wbs@gmail.com

