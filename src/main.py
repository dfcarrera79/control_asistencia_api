# import ssl
import uvicorn
from fastapi import FastAPI
from src.config import config
from src.routers import turnos
from src.routers import selfie
from src.routers import usuarios
from src.routers import recargas
from src.routers import registros
from src.routers import empleados
from src.routers import almacenes
from src.routers import exepciones
from src.routers import asistencias
from src.routers import dispositivos
from src.routers import consolidaciones
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
# from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app = FastAPI(
    title="Control de Asistencia API",
    description="Back end desarrollado para el control de asistencia de los empleados",
    version="1.0.0",
    contact={
        "name": "Diego Carrera",
        "url": "http://loxasoluciones.com/",
        "email": "dfcarrera@outlook.com",
    }
)

# # Use HTTPSRedirectMiddleware to redirect HTTP to HTTPS
# app.add_middleware(HTTPSRedirectMiddleware)

# API endpoints
app.include_router(turnos.router)
app.include_router(selfie.router)
app.include_router(usuarios.router)
app.include_router(recargas.router)
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

app.mount("/static", StaticFiles(directory="src/public/fotos"), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

# # SSL Configuration
# ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
# ssl_context.load_cert_chain(config.ssl_certfile, keyfile=config.ssl_keyfile)

# if __name__ == "__main__":
#     uvicorn.run("src.main:app", host="0.0.0.0",
#                 port=8000, ssl=ssl_context, reload=True)
