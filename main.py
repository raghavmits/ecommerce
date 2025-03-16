# main.py
from fastapi import FastAPI
import uvicorn
from routes.users import router as user_router
from routes.products import router as product_router
from routes.carts import router as cart_router

app = FastAPI()

# Include the routers
app.include_router(user_router)
app.include_router(product_router)
app.include_router(cart_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
