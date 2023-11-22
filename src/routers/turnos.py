import json
from sqlite3 import IntegrityError
import fastapi
from src.config import config
from src.utils import utils
from src.middleware import token_middleware, acceso_middleware
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


@router.post("/registrar_turno")
async def registrar_turno(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    nombre = data['nombre']
    dias_trabajados = data['dias_trabajados']
    inicio1 = data['inicio1']
    fin1 = data['fin1']
    inicio2 = data['inicio2']
    fin2 = data['fin2']

    sql = ""
    if (inicio2 == "00:00" and fin2 == "00:00"):
        sql = f"INSERT INTO rol.tturnos (nombre, dias_trabajados, inicio1, fin1) VALUES ('{nombre}', '{dias_trabajados}', '{inicio1}', '{fin1}') RETURNING codigo"

    if (inicio2 != "00:00" and fin2 != "00:00"):
        sql = f"INSERT INTO rol.tturnos (nombre, dias_trabajados, inicio1, fin1, inicio2, fin2) VALUES ('{nombre}', '{dias_trabajados}', '{inicio1}', '{fin1}', '{inicio2}', '{fin2}') RETURNING codigo"

    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 826, 1)

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
            return {"error": "N", "mensaje": "Registro de horario exitoso", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.put("/actualizar_turno")
async def actualizar_turno(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    codigo = data['codigo']
    nombre = data['nombre']
    inicio1 = data['inicio1']
    fin1 = data['fin1']
    inicio2 = data['inicio2']
    fin2 = data['fin2']
    dias_trabajados = data['dias_trabajados']

    sql = ""
    if (inicio2 == "00:00" and fin2 == "00:00"):
        sql = f"UPDATE rol.tturnos SET nombre = '{nombre}', inicio1 = '{inicio1}', fin1 = '{fin1}', dias_trabajados = '{dias_trabajados}' WHERE codigo = {codigo} RETURNING codigo"

    if (inicio2 != "00:00" and fin2 != "00:00"):
        sql = f"UPDATE rol.tturnos SET nombre = '{nombre}', inicio1 = '{inicio1}', fin1 = '{fin1}', inicio2 = '{inicio2}', fin2 = '{fin2}', dias_trabajados = '{dias_trabajados}' WHERE codigo = {codigo} RETURNING codigo"

    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 826, 2)

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
            return {"error": "N", "mensaje": "El horario se ha actualizado correctamente", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.get("/obtener_turnos")
async def obtener_turnos(request: Request):
    sql = f"SELECT * FROM rol.tturnos"
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

            turnos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": turnos}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.delete("/eliminar_turno")
async def eliminar_turno(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    codigo = data['codigo']
    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 826, 3)

    if acceso[0]['tiene_acceso'] != '':
        return {
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }

    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            # Verificar si hay registros relacionados en tturnosasignados
            check_sql = f"SELECT COUNT(*) FROM rol.tturnosasignados WHERE turno_codigo = {codigo}"
            count = session.execute(text(check_sql)).scalar()
            if count > 0:
                return {"error": "S", "mensaje": "No se puede eliminar el horario porque está asignado"}

            sql = f"DELETE FROM rol.tturnos WHERE codigo = {codigo} RETURNING codigo"
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Horario eliminado correctamente", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.get("/obtener_horarios")
async def obtener_horarios(request: Request):
    sql = f"SELECT codigo, nombre, inicio1, fin1, inicio2, fin2 FROM rol.tturnos"
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

            horarios = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": horarios}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.post("/asignar_horario")
async def asignar_horario(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    usuario_codigo = data['usuario_codigo']
    turno_codigo = data['turno_codigo']
    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 827, 1)

    if acceso[0]['tiene_acceso'] != '':
        return {
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }
    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            # Contar las asignaciones existentes para el usuario
            existing_assignments = session.execute(
                text(
                    f"SELECT COUNT(*) FROM rol.tturnosasignados WHERE usuario_codigo = {usuario_codigo}")
            ).scalar()

            if existing_assignments >= 2:
                return {"error": "S", "mensaje": "No se pueden asignar más de dos turnos por usuario."}

            sql = f"INSERT INTO rol.tturnosasignados (usuario_codigo, turno_codigo) VALUES ('{usuario_codigo}', '{turno_codigo}') RETURNING codigo"

            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Horario asignado correctamente", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.get("/obtener_lugar_horario")
async def obtener_lugar_horario(request: Request):
    sql = f"SELECT talmacen.alm_nomcom FROM rol.tlugaresasignados INNER JOIN rol.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN comun.talmacen ON talmacen.alm_codigo = tcoordenadas.alm_codigo INNER JOIN rol.tturnosasignados ON tturnosasignados.usuario_codigo = tlugaresasignados.usuario_codigo"
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
