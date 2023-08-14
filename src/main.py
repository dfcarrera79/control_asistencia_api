from fastapi import FastAPI
from src.routers import usuarios
from src.routers import empleados
from src.routers import almacenes
from src.routers import dispositivos
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# API endpoints
app.include_router(usuarios.router)
app.include_router(empleados.router)
app.include_router(almacenes.router)
app.include_router(dispositivos.router)

# Allow all origins in CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
