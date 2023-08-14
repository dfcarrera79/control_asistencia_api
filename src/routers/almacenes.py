import json
import fastapi
from src import config
from src.utils import utils
from sqlalchemy.orm import Session
from fastapi import HTTPException, Request
from sqlalchemy import create_engine, text


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
        if not utils.verify_token(token):
            raise HTTPException(
                status_code=401, detail="Usuario no autorizado")
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
    try:
        sql = f"INSERT INTO comun.tcoordenadas (alm_codigo, lat, long) VALUES ('{alm_codigo}', '{lat}', '{long}') RETURNING codigo"
        print('[SQL]: ', sql)
        token = request.headers.get('token')
        if not utils.verify_token(token):
            raise HTTPException(
                status_code=401, detail="Usuario no autorizado")
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
    try:
        sql = f"UPDATE comun.tcoordenadas SET lat = '{lat}', long = '{long}' WHERE alm_codigo = '{alm_codigo}' RETURNING codigo"
        print('[SQL]: ', sql)
        token = request.headers.get('token')
        if not utils.verify_token(token):
            raise HTTPException(
                status_code=401, detail="Usuario no autorizado")
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
        if not utils.verify_token(token):
            raise HTTPException(
                status_code=401, detail="Usuario no autorizado")
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
    sql = f"SELECT a.alm_codigo, a.alm_nomcom, a.alm_calles, a.alm_ciud, c.lat, c.long FROM comun.talmacen a INNER JOIN comun.tcoordenadas c ON a.alm_codigo = c.alm_codigo"
    token = request.headers.get('token')
    try:
        if not utils.verify_token(token):
            raise HTTPException(
                status_code=401, detail="Usuario no autorizado")
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
    try:
        sql = f"UPDATE comun.tcoordenadas SET usuario_codigo = '{usuario_codigo}' WHERE alm_codigo = '{alm_codigo}' RETURNING codigo"
        print('[SQL]: ', sql)
        token = request.headers.get('token')
        if not utils.verify_token(token):
            raise HTTPException(
                status_code=401, detail="Usuario no autorizado")
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Las coordenadas se han actualizado", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}
