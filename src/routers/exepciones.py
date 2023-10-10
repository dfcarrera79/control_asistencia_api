import json
import fastapi
from src import config
from src.utils import utils
from datetime import datetime
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text

# Establish connections to PostgreSQL databases for "reclamos" and "apromed" respectively
db_uri1 = config.db_uri1
engine1 = create_engine(db_uri1)

db_uri2 = config.db_uri2
engine2 = create_engine(db_uri2)

# API Route Definitions
router = fastapi.APIRouter()


@router.get("/obtener_empleados_lugares")
async def obtener_empleados_lugares(request: Request):
    sql = f"SELECT templeado.codigo as usuario_codigo, templeado.nombres || ' ' || templeado.apellidos AS nombre_completo, talmacen.alm_nomcom FROM comun.tlugaresasignados INNER JOIN comun.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN comun.talmacen ON talmacen.alm_codigo = tcoordenadas.alm_codigo INNER JOIN rol.templeado ON tlugaresasignados.usuario_codigo = templeado.codigo ORDER BY nombre_completo"
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

            asignados = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": asignados}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.post("/registrar_exepcion")
async def registrar_exepcion(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    usuario_codigo = data['usuario_codigo']
    excepcion = data['excepcion']
    dias = data['dias']
    token = request.headers.get('token')
    sql = f"INSERT INTO comun.texcepciones (usuario_codigo, excepcion, dias) VALUES ('{usuario_codigo}', '{excepcion.strip()}', ARRAY{dias}) RETURNING id"
    try:
        if not utils.verify_token(token):
            raise HTTPException(
                status_code=401, detail="Usuario no autorizado")
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Registro de excepción exitoso", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.put("/autorizar_exepcion")
async def autorizar_exepcion(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    usuario_codigo = data['usuario_codigo']
    autorizado_por = data['autorizado_por']
    token = request.headers.get('token')
    sql = f"UPDATE comun.texcepciones SET autorizado_por = '{autorizado_por}', autorizado = true WHERE id = '{usuario_codigo}' RETURNING id"

    try:
        if not utils.verify_token(token):
            raise HTTPException(
                status_code=401, detail="Usuario no autorizado")
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Excepción autorizada con exitoso", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.put("/desautorizar_exepcion")
async def desautorizar_exepcion(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    id = data['id']
    token = request.headers.get('token')
    sql = f"UPDATE comun.texcepciones SET autorizado_por = NULL, autorizado = false WHERE id = {id} RETURNING id"

    try:
        if not utils.verify_token(token):
            raise HTTPException(
                status_code=401, detail="Usuario no autorizado")
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "La autorización se ha eliminado con éxito.", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.get("/obtener_excepciones")
async def obtener_excepciones(request: Request):
    token = request.headers.get('token')
    sql = "SELECT texcepciones.id as usuario_codigo, templeado.nombres || ' ' || templeado.apellidos AS nombre_completo, talmacen.alm_nomcom, texcepciones.excepcion, texcepciones.dias FROM comun.tlugaresasignados INNER JOIN comun.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN comun.talmacen ON talmacen.alm_codigo = tcoordenadas.alm_codigo INNER JOIN rol.templeado ON tlugaresasignados.usuario_codigo = templeado.codigo INNER JOIN comun.texcepciones ON texcepciones.usuario_codigo = templeado.codigo WHERE texcepciones.autorizado = false ORDER BY nombre_completo"
    try:
        if not utils.verify_token(token):
            raise HTTPException(
                status_code=401, detail="Usuario no autorizado")
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Registro de excepción exitoso", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.get("/obtener_excepciones_autorizadas")
async def obtener_excepciones_autorizadas(request: Request, desde: str = None, hasta: str = None):
    token = request.headers.get('token')
    sql = "SELECT texcepciones.id, templeado.nombres || ' ' || templeado.apellidos AS nombre_completo, texcepciones.excepcion, texcepciones.dias, templeado2.nombres || ' ' || templeado2.apellidos AS autorizado_por FROM comun.texcepciones INNER JOIN rol.templeado AS templeado ON texcepciones.usuario_codigo = templeado.codigo INNER JOIN rol.templeado AS templeado2 ON texcepciones.autorizado_por = templeado2.codigo WHERE texcepciones.autorizado = TRUE"

    try:
        if not utils.verify_token(token):
            raise HTTPException(
                status_code=401, detail="Usuario no autorizado")

        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]

            # Si se proporcionan fechas "desde" y "hasta", filtra las excepciones por ese rango
            if desde and hasta:
                objetos = [obj for obj in objetos if all(
                    desde <= fecha <= hasta for fecha in obj["dias"])]

            return {"error": "N", "mensaje": "Registro de excepción exitoso", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}
