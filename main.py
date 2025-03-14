# main.py
from fastapi import FastAPI
import uvicorn
from routes.users import router as user_router

app = FastAPI()

# Include the router for user-related routes
app.include_router(user_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
