# import ssl
import uvicorn
from fastapi import FastAPI
from routers import turnos
from routers import selfie
from routers import usuarios
from routers import registros
from routers import empleados
from routers import almacenes
from routers import exepciones
from routers import asistencias
from routers import dispositivos
from routers import consolidaciones
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
