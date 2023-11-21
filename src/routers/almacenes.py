import json
import math
import fastapi
from src import config
from fastapi import Request
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from src.middleware import token_middleware, acceso_middleware

# Establish connections to PostgreSQL databases for "reclamos" and "apromed" respectively
db_uri1 = config.db_uri1
engine1 = create_engine(db_uri1)

db_uri2 = config.db_uri2
engine2 = create_engine(db_uri2)

# API Route Definitions
router = fastapi.APIRouter()


@router.get("/obtener_almacenes")
async def obtener_almacenes(request: Request):
    sql = f"SELECT alm_codigo, alm_nomcom, alm_calles, alm_pais, alm_ciud, alm_tlf1, alm_tlf2 FROM comun.talmacen"
    token = request.headers.get('token')
    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": "",
                    "objetos": rows,
                }

            almacenes = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": almacenes}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.post("/registrar_coordenadas")
async def registrar_coordenadas(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    alm_codigo = data['alm_codigo']
    lat = data['lat']
    long = data['long']
    sql = f"INSERT INTO comun.tcoordenadas (alm_codigo, lat, long) VALUES ('{alm_codigo}', '{lat}', '{long}') RETURNING codigo"
    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 820, 1)

    if acceso[0]['tiene_acceso'] != '':
        return {
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }
    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Registro de coordenadas exitoso", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.put("/actualizar_coordenadas")
async def actualizar_coordenadas(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    alm_codigo = data['alm_codigo']
    lat = data['lat']
    long = data['long']
    sql = f"UPDATE comun.tcoordenadas SET lat = '{lat}', long = '{long}' WHERE alm_codigo = '{alm_codigo}' RETURNING codigo"
    token = request.headers.get('token')
    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Las coordenadas se han actualizado", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.get("/obtener_coordenadas")
async def obtener_coordenadas(request: Request, alm_codigo: int):
    sql = f"SELECT codigo, lat, long FROM comun.tcoordenadas WHERE alm_codigo={alm_codigo}"
    token = request.headers.get('token')
    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": "",
                    "objetos": rows,
                }

            coordenadas = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": coordenadas}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.get("/obtener_coordenadas_almacen")
async def obtener_coordenadas(alm_nomcom: str):
    sql = f"SELECT lat, long FROM comun.tcoordenadas INNER JOIN comun.talmacen ON talmacen.alm_codigo = tcoordenadas.alm_codigo WHERE alm_nomcom LIKE '{alm_nomcom}'"
    try:
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": "",
                    "objetos": rows,
                }

            coordenadas = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": coordenadas}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.get("/obtener_lugares")
async def obtener_lugares(request: Request):
    sql = f"SELECT c.codigo, a.alm_nomcom, a.alm_calles, a.alm_ciud, c.lat, c.long FROM comun.talmacen a INNER JOIN comun.tcoordenadas c ON a.alm_codigo = c.alm_codigo"
    token = request.headers.get('token')
    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": "",
                    "objetos": rows,
                }

            lugares = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": lugares}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.put("/designar_lugar_empleado")
async def designar_lugar_empleado(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    usuario_codigo = data['usuario_codigo']
    alm_codigo = data['alm_codigo']
    sql = f"INSERT INTO comun.tlugaresasignados (coordenadas_codigo, usuario_codigo) VALUES ('{alm_codigo}', '{usuario_codigo}') ON CONFLICT (usuario_codigo) DO UPDATE SET coordenadas_codigo = {alm_codigo} RETURNING codigo"
    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 821, 1)

    if acceso[0]['tiene_acceso'] != '':
        return {
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }
    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Empleado asignado a lugar de trabajo", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.get("/obtener_lugar_empleado")
async def obtener_lugar_empleado(request: Request):
    sql = f"SELECT talmacen.alm_nomcom AS lugares FROM comun.tlugaresasignados INNER JOIN comun.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN comun.talmacen ON talmacen.alm_codigo = tcoordenadas.alm_codigo"
    token = request.headers.get('token')
    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": "",
                    "objetos": rows,
                }

            lugares = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": lugares}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.get("/obtener_lugares_asignados")
async def obtener_lugares_asignados(request: Request):
    sql = f"SELECT alm_codigo FROM comun.tcoordenadas ORDER BY alm_codigo"
    token = request.headers.get('token')
    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": "",
                    "objetos": rows,
                }

            return {"error": "N", "mensaje": "", "objetos": rows}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}
