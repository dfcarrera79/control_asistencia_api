from fastapi import FastAPI
from src.config import config
from src.routers import turnos
from src.routers import selfie
from src.routers import usuarios
from src.routers import registros
from src.routers import empleados
from src.routers import almacenes
from src.routers import exepciones
from src.routers import asistencias
from src.routers import dispositivos
from src.routers import consolidaciones
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# API endpoints
app.include_router(turnos.router)
app.include_router(selfie.router)
app.include_router(usuarios.router)
app.include_router(registros.router)
app.include_router(empleados.router)
app.include_router(almacenes.router)
app.include_router(exepciones.router)
app.include_router(asistencias.router)
app.include_router(dispositivos.router)
app.include_router(consolidaciones.router)

# Allow all origins in CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fotos_dir = config.path2
app.mount("/static", StaticFiles(directory=fotos_dir))
