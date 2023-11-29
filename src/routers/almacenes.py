import json
import fastapi
from fastapi import Request
from src.config import config
from sqlalchemy import create_engine
from src.routers.controllers import SessionHandler
from src.middleware import acceso_middleware

# Establish connections to PostgreSQL databases for "reclamos" and "apromed" respectively
engine = create_engine(config.db_uri2)

# API Route Definitions
router = fastapi.APIRouter()

# Crear una instancia de la clase con tu motor de base de datos
query_handler = SessionHandler(engine)


@router.get("/obtener_almacenes")
async def obtener_almacenes(request: Request):
    sql = f"SELECT alm_codigo, alm_nomcom, alm_calles, alm_pais, alm_ciud, alm_tlf1, alm_tlf2 FROM comun.talmacen"
    token = request.headers.get('token')
    return query_handler.execute_sql_token(sql, token, "")


@router.post("/registrar_coordenadas")
async def registrar_coordenadas(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    alm_codigo = data['alm_codigo']
    lat = data['lat']
    long = data['long']
    sql = f"INSERT INTO rol.tcoordenadas (alm_codigo, lat, long) VALUES ('{alm_codigo}', '{lat}', '{long}') RETURNING codigo"
    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 820, 1)

    if acceso[0]['tiene_acceso'] != '':
        return {
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }

    return query_handler.execute_sql_token(sql, token, "Registro de coordenadas exitoso")


@router.put("/actualizar_coordenadas")
async def actualizar_coordenadas(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    alm_codigo = data['alm_codigo']
    lat = data['lat']
    long = data['long']
    sql = f"UPDATE rol.tcoordenadas SET lat = '{lat}', long = '{long}' WHERE alm_codigo = '{alm_codigo}' RETURNING codigo"
    token = request.headers.get('token')
    return query_handler.execute_sql_token(sql, token, "Las coordenadas se han actualizado")


@router.get("/obtener_coordenadas")
async def obtener_coordenadas(request: Request, alm_codigo: int):
    sql = f"SELECT codigo, lat, long FROM rol.tcoordenadas WHERE alm_codigo={alm_codigo}"
    token = request.headers.get('token')
    return query_handler.execute_sql_token(sql, token, "")


@router.get("/obtener_coordenadas_almacen")
async def obtener_coordenadas(alm_nomcom: str):
    sql = f"SELECT lat, long FROM rol.tcoordenadas INNER JOIN comun.talmacen ON talmacen.alm_codigo = tcoordenadas.alm_codigo WHERE alm_nomcom LIKE '{alm_nomcom}'"
    return query_handler.execute_sql(sql, "")


@router.get("/obtener_lugares")
async def obtener_lugares(request: Request):
    sql = f"SELECT c.codigo, a.alm_nomcom, a.alm_calles, a.alm_ciud, c.lat, c.long FROM comun.talmacen a INNER JOIN rol.tcoordenadas c ON a.alm_codigo = c.alm_codigo"
    token = request.headers.get('token')
    return query_handler.execute_sql_token(sql, token, "")


@router.put("/designar_lugar_empleado")
async def designar_lugar_empleado(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    usuario_codigo = data['usuario_codigo']
    alm_codigo = data['alm_codigo']
    sql = f"INSERT INTO rol.tlugaresasignados (coordenadas_codigo, usuario_codigo) VALUES ('{alm_codigo}', '{usuario_codigo}') ON CONFLICT (usuario_codigo) DO UPDATE SET coordenadas_codigo = {alm_codigo} RETURNING codigo"
    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 821, 1)

    if acceso[0]['tiene_acceso'] != '':
        return {
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }

    return query_handler.execute_sql_token(sql, token, "Empleado asignado a lugar de trabajo")


@router.get("/obtener_lugar_empleado")
async def obtener_lugar_empleado(request: Request):
    sql = f"SELECT talmacen.alm_nomcom AS lugares FROM rol.tlugaresasignados INNER JOIN rol.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN comun.talmacen ON talmacen.alm_codigo = tcoordenadas.alm_codigo"
    token = request.headers.get('token')
    return query_handler.execute_sql_token(sql, token, "")


@router.get("/obtener_lugares_asignados")
async def obtener_lugares_asignados(request: Request):
    sql = f"SELECT alm_codigo FROM rol.tcoordenadas ORDER BY alm_codigo"
    token = request.headers.get('token')
    return query_handler.execute_sql_token(sql, token, "")
