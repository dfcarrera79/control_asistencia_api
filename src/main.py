from fastapi import FastAPI
from src.routers import usuarios
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# API endpoints
app.include_router(usuarios.router)

# Allow all origins in CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
