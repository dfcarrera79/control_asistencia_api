import json
import fastapi
from fastapi import Request
from src.utils import utils
from src.config import config
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from src.routers.controllers import SessionHandler
from src.middleware import token_middleware, acceso_middleware


# Establish connections to PostgreSQL databases for "apromed"
engine = create_engine(config.db_uri)

# API Route Definitions
router = fastapi.APIRouter()

# Crear una instancia de la clase con tu motor de base de datos
query_handler = SessionHandler(engine)


async def horarios(codigo: int):
    sql = f"SELECT nombre, horario, mes, anio FROM rol.thorario WHERE codigo = {codigo}"
    with Session(engine) as session:
        rows = session.execute(text(sql)).fetchall()
        objetos = [row._asdict() for row in rows]
        return objetos


@router.post("/registrar_horario")
async def registrar_horario(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    nombre = data['nombre']
    horario = data['horario']
    mes = data['mes']
    anio = data['anio']
    sql = f"INSERT INTO rol.thorario (nombre, horario, mes, anio) VALUES ('{nombre}', '{horario}', '{mes}', '{anio}') RETURNING codigo"
    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 826, 1)
    if acceso[0]['tiene_acceso'] != '':
        return {
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }

    return query_handler.execute_sql_token(sql, token, "Registro de horario exitoso")


@router.get("/obtener_horarios")
async def obtener_horarios(request: Request):
    sql = f"SELECT * FROM rol.thorario"
    token = request.headers.get('token')
    return query_handler.execute_sql_token(sql, token, "")

@router.get("/obtener_horarios_fecha")
async def obtener_horarios_fecha(request: Request, mes: str, anio: str):
    sql = f"SELECT * FROM rol.thorario WHERE codigo != 0"
    token = request.headers.get('token')
    
    nuevo_mes = utils.obtener_numero_mes(mes)
    
    if mes not in [None, '', 'N', '0']:
        sql += f" AND thorario.mes = {nuevo_mes}"

    if anio not in [None, '', 'N', '0']:
        sql += f" AND thorario.anio = {int(anio)}"

    sql += " ORDER BY anio"
    
    return query_handler.execute_sql_token(sql, token, "")


@router.put("/actualizar_horario")
async def actualizar_horario(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    codigo = data['codigo']
    nombre = data['nombre']
    horario = data['horario']
    mes = data['mes']
    anio = data['anio']
    sql = f"UPDATE rol.thorario SET nombre = '{nombre}', horario = '{horario}', mes = '{mes}', anio = '{anio}' WHERE codigo = {codigo} RETURNING codigo"
    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 826, 2)
    if acceso[0]['tiene_acceso'] != '':
        return {
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }

    return query_handler.execute_sql_token(sql, token, "El horario se ha actualizado correctamente")


@router.put("/editar_horario_empleado")
async def editar_horario_empleado(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    usucodigo = request.headers.get('usucodigo')
    auditoria_text = f"usuario: {data['usuario']} {data['textoHorario']}\nmodificado_por: {data['modificadoPor']}"
    
    sql = f"""
    UPDATE rol.thorariosasignados
    SET horario = '{data['horario']}', 
        auditoria = CASE 
                        WHEN auditoria IS NULL THEN ''
                        ELSE auditoria || '\n-------\n'
                    END || '{auditoria_text}'
    WHERE codigo = {data['codigo']} RETURNING codigo
    """
    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 826, 2)
    if acceso[0]['tiene_acceso'] != '':
        return {
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }

    return query_handler.execute_sql_token(sql, token, "El horario se ha actualizado correctamente")


@router.delete("/eliminar_horario")
async def eliminar_horario(request: Request):
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
        with Session(engine) as session:
            # Verificar si hay registros relacionados en tturnosasignados
            # check_sql = f"SELECT COUNT(*) FROM rol.tturnosasignados WHERE turno_codigo = {codigo}"
            # count = session.execute(text(check_sql)).scalar()
            # if count > 0:
            #     return {"error": "S", "mensaje": "No se puede eliminar el horario porque está asignado"}
            sql = f"DELETE FROM rol.thorario WHERE codigo = {codigo} RETURNING codigo"
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Horario eliminado correctamente", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.post("/clonar_horario")
async def clonar_horario(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    codigo = data['codigo']
    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 826, 3)
    if acceso[0]['tiene_acceso'] != '':
        return JSONResponse(content={
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }, status_code=403)
    try:
        token_middleware.verify_token(token)
        with Session(engine) as session:
            # Obtener el horario a clonar
            horario_original = await horarios(codigo)
            if not horario_original:
                return {
                    "error": "S",
                    "mensaje": "No se encontró el horario a clonar",
                    "objetos": "",
                }
            
            sql = f"INSERT INTO rol.thorario (nombre, horario, mes, anio) VALUES ('{horario_original[0]['nombre']} clonado', '{json.dumps(horario_original[0]['horario'])}', '{horario_original[0]['mes']}', '{horario_original[0]['anio']}') RETURNING codigo"
            
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Horario clonado correctamente", "objetos": objetos}
            
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


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

    return query_handler.execute_sql_token(sql, token, "Registro de horario exitoso")


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

    return query_handler.execute_sql_token(sql, token, "El horario se ha actualizado correctamente")


@router.get("/obtener_turnos")
async def obtener_turnos(request: Request):
    sql = f"SELECT * FROM rol.tturnos"
    token = request.headers.get('token')
    return query_handler.execute_sql_token(sql, token, "")


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
        with Session(engine) as session:
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
        with Session(engine) as session:
            
            respuesta = await horarios(turno_codigo)
            
            new_query = f"SELECT COUNT(*) FROM rol.thorariosasignados WHERE usuario_codigo = {usuario_codigo} AND mes = {respuesta[0]['mes']} AND anio = {respuesta[0]['anio']}"
            
            # Contar las asignaciones existentes para el usuario
            existing_assignments = session.execute(
                text(new_query)
            ).scalar()

            if existing_assignments >= 1:
                return {"error": "S", "mensaje": "Ya existe un horario asignado para el mes y año seleccionado."}
            
            sql = f"INSERT INTO rol.thorariosasignados (usuario_codigo, horario_codigo, horario, mes, anio, lugar_codigo, nombre_horario) VALUES ('{usuario_codigo}', '{turno_codigo}', '{json.dumps(respuesta[0]['horario'])}', '{respuesta[0]['mes']}', '{respuesta[0]['anio']}', '{data['lugar_codigo']}', '{data['nombre_horario']}') RETURNING codigo"

            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Horario asignado correctamente", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.get("/obtener_lugar_horario")
async def obtener_lugar_horario(request: Request):
    sql = f"SELECT talmacen.alm_nomcom FROM rol.thorariosasignados INNER JOIN comun.talmacen ON talmacen.alm_codigo = rol.thorariosasignados.lugar_codigo"
    token = request.headers.get('token')
    return query_handler.execute_sql_token(sql, token, "")
