# main.py
from fastapi import FastAPI
import uvicorn
from contextlib import asynccontextmanager
from routes.users import router as user_router
from routes.products import router as product_router
from routes.carts import router as cart_router
from database import create_indexes

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create indexes
    await create_indexes()
    print("Application started and indexes created")
    yield
    # Shutdown: cleanup could go here
    print("Application shutting down")

app = FastAPI(lifespan=lifespan)

# Include the routers
app.include_router(user_router)
app.include_router(product_router)
app.include_router(cart_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
