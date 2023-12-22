import os
import json
import shutil
import fastapi
from PIL import Image
from utils import utils
from config import config
from pydantic import BaseModel
from urllib.parse import unquote
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from fastapi import Request, UploadFile, File
from routers.controllers import SessionHandler
from middleware import token_middleware, acceso_middleware

# Models
class RegistrarModel(BaseModel):
    filepath: str
    codigo: int


# Establish connections to PostgreSQL databases for "apromed"
engine = create_engine(config.db_uri2)

# Crear una instancia de la clase con tu motor de base de datos
query_handler = SessionHandler(engine)

# API Route Definitions
router = fastapi.APIRouter()


async def horarios_asignados(codigo: int):
    sql = f"SELECT turno_codigo FROM rol.tturnosasignados WHERE usuario_codigo = {codigo}"
    with Session(engine) as session:
        rows = session.execute(text(sql)).fetchall()
        objetos = [row._asdict() for row in rows]
        return objetos


async def lugar_asignado(codigo: int):
    sql = f"SELECT coordenadas_codigo FROM rol.tlugaresasignados WHERE usuario_codigo = {codigo}"
    with Session(engine) as session:
        rows = session.execute(text(sql)).fetchall()
        objetos = [row._asdict() for row in rows]
        return objetos


@router.post("/registrar_horas_suplementarias")
async def registrar_horas_suplementarias(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    usuario_codigo = data['usuario_codigo']
    fecha = data['fecha']
    horas = data['horas']
    asignado_por = data['asignadoPor']
    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 830, 1)
    sql = f"INSERT INTO rol.thoras_suplementarias (usuario_codigo, fecha, horas, asignado_por) VALUES ({usuario_codigo}, '{fecha}', {horas}, {asignado_por}) RETURNING codigo"

    if acceso[0]['tiene_acceso'] != '':
        return {
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }

    return query_handler.execute_sql_token(sql, token, "Registro de horas suplementarias exitoso")


@router.delete('/eliminar_suplementarias')
async def eliminar_suplementarias(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    codigo = data['codigo']
    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 831, 3)

    if acceso[0]['tiene_acceso'] != '':
        return {
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }

    sql = f"DELETE FROM rol.thoras_suplementarias WHERE codigo = {codigo} RETURNING codigo"

    return query_handler.execute_sql_token(sql, token, "Registro de horas suplementarias eliminado exitosamente")


@router.get("/obtener_horas_suplementarias")
async def obtener_horas_suplementarias(request: Request, departamento, desde: str, hasta: str):
    token = request.headers.get('token')
    sql = "SELECT TS.codigo, TEmpleado.nombres || ' ' || TEmpleado.apellidos AS nombre_completo_usuario, TPlantillaRol.descripcion AS departamento, TS.fecha, TS.horas, TUsuario.usu_nomape AS asignado_por FROM rol.thoras_suplementarias TS INNER JOIN rol.TEmpleado TEmpleado ON TS.usuario_codigo = TEmpleado.codigo INNER JOIN usuario.TUsuario TUsuario ON TS.asignado_por = TUsuario.usu_codigo INNER JOIN rol.TPlantillaRol ON TEmpleado.codigo_plantilla = TPlantillaRol.codigo"

    if departamento not in [None, '', 'N']:
        sql += f" WHERE TPlantillaRol.descripcion LIKE '{departamento}'"

    if desde not in [None, '', 'N'] and hasta not in [None, '', 'N']:
        sql += f" WHERE CAST(fecha as date) BETWEEN '{desde}' AND '{hasta}'"

    sql += " ORDER BY nombre_completo_usuario"

    return query_handler.execute_sql_token(sql, token, "")


@router.post("/registrar_entrada")
async def registrar_entrada(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    employee_id = data['employee_id']
    horarios = await horarios_asignados(employee_id)

    if len(horarios) == 0:
        return {"error": "S", "mensaje": "No tiene horarios asignados"}

    lugar = await lugar_asignado(employee_id)

    if len(lugar) == 0:
        return {"error": "S", "mensaje": "No tiene un lugar de trabajo asignado"}

    sql = f"INSERT INTO rol.tasistencias (usuario_codigo, entrada, horarios, lugar_asignado) VALUES ({employee_id}, NOW(), '{json.dumps(horarios)}', {lugar[0]['coordenadas_codigo']}) RETURNING codigo"

    return query_handler.execute_sql(sql, "Registro de entrada exitoso")


@router.put("/registrar_salida")
async def registrar_salida(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    employee_id = data['employee_id']
    horarios = await horarios_asignados(employee_id)

    if len(horarios) == 0:
        return {"error": "S", "mensaje": "No tiene horarios asignados"}

    lugar = await lugar_asignado(employee_id)

    if len(lugar) == 0:
        return {"error": "S", "mensaje": "No tiene un lugar de trabajo asignado"}

    sql = f"UPDATE rol.tasistencias SET salida = NOW() WHERE codigo = (SELECT codigo FROM rol.tasistencias WHERE usuario_codigo = {employee_id} ORDER BY entrada DESC LIMIT 1) AND salida IS NULL RETURNING codigo"

    return query_handler.execute_sql(sql, "Registro de salida exitoso")


@router.get("/obtener_numero_paginas")
async def obtener_numero_paginas(request: Request, usuario_codigo, fecha_desde, fecha_hasta):
    token = request.headers.get('token')
    sql = f"SELECT COUNT(*) FROM rol.tasistencias WHERE usuario_codigo = {usuario_codigo} AND entrada BETWEEN '{fecha_desde}' AND '{fecha_hasta}'"

    return query_handler.execute_sql_token(sql, token, "")


@router.get("/obtener_numero_paginas_atrasos")
async def obtener_numero_paginas_atrasos(request: Request, usuario_codigo, fecha_desde, fecha_hasta):
    token = request.headers.get('token')

    objetos = await obtener_atrasos(request, usuario_codigo, fecha_desde, fecha_hasta)

    try:
        token_middleware.verify_token(token)

        if len(objetos) == 0:
            return {
                "error": "S",
                "mensaje": "",
                "objetos": objetos,
            }

        return {"error": "N", "mensaje": "", "objetos": len(objetos)}

    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.get("/obtener_atrasos")
async def obtener_atrasos(request: Request, usuario_codigo, fecha_desde, fecha_hasta):

    fecha_hasta = datetime.strptime(fecha_hasta, '%Y/%m/%d')
    fecha_hasta = fecha_hasta + timedelta(days=1) - timedelta(seconds=1)

    query = f"SELECT tasistencias.codigo, templeado.nombres || ' ' || templeado.apellidos AS nombre_completo, talmacen.alm_nomcom as lugar_asignado, entrada, salida FROM rol.tasistencias INNER JOIN rol.templeado ON tasistencias.usuario_codigo = templeado.codigo INNER JOIN rol.tlugaresasignados ON tasistencias.usuario_codigo = tlugaresasignados.usuario_codigo INNER JOIN rol.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN comun.talmacen ON talmacen.alm_codigo = tcoordenadas.alm_codigo WHERE tasistencias.usuario_codigo = {usuario_codigo} AND entrada BETWEEN '{fecha_desde}' AND '{fecha_hasta}' ORDER BY entrada"

    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 832, 1)

    if acceso[0]['tiene_acceso'] != '':
        return {
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }

    with Session(engine) as session:
        rows = session.execute(text(query)).fetchall()
        if len(rows) == 0:
            return {
                "error": "S",
                "mensaje": "",
                "objetos": rows,
            }

        asistencias = [row._asdict() for row in rows]
        excepciones = await excepciones_autorizadas(usuario_codigo)

        nuevas_asistencias = []
        for diccionario in asistencias:
            fecha = diccionario['entrada'].strftime('%Y/%m/%d')
            if fecha not in excepciones:
                nuevas_asistencias.append(diccionario)

    horarios = await get_horarios(usuario_codigo)

    turnos = []

    for horario in horarios:
        info = await get_horario_info(horario)
        turnos.append(info[0])

    try:
        token_middleware.verify_token(token)

        atrasos = []

        for turno in turnos:
            dias_trabajados = turno["dias_trabajados"]

            if isinstance(dias_trabajados, list):
                inicio1 = datetime.strptime(turno["inicio1"], '%H:%M').time()
                fin1 = datetime.strptime(turno["fin1"], '%H:%M').time()
                if turno["inicio2"] and turno["fin2"]:
                    inicio2 = datetime.strptime(
                        turno["inicio2"], '%H:%M').time()
                    fin2 = datetime.strptime(turno["fin2"], '%H:%M').time()
                else:
                    inicio2 = None
                    fin2 = None

                for asistencia in nuevas_asistencias:
                    entrada = asistencia["entrada"]

                    for rango in dias_trabajados:
                        entrada = asistencia["entrada"]

                        fecha_inicio = datetime.strptime(
                            rango["from"], "%Y/%m/%d")
                        fecha_fin = datetime.strptime(
                            rango["to"], "%Y/%m/%d") + timedelta(days=1) - timedelta(seconds=1)

                        if fecha_inicio <= entrada <= fecha_fin:
                            if inicio1 <= entrada.time() <= fin1:

                                atraso = entrada - \
                                    datetime.combine(entrada.date(), inicio1)
                                if atraso.total_seconds() > 300:
                                    atrasos.append(asistencia)

                            if inicio2 and fin2:
                                if inicio2 <= entrada.time() <= fin2:

                                    atraso = entrada - \
                                        datetime.combine(
                                            entrada.date(), inicio2)
                                    if atraso.total_seconds() > 300:
                                        atrasos.append(asistencia)

            else:
                inicio1 = datetime.strptime(turno["inicio1"], '%H:%M').time()
                fin1 = datetime.strptime(turno["fin1"], '%H:%M').time()
                if turno["inicio2"] and turno["fin2"]:
                    inicio2 = datetime.strptime(
                        turno["inicio2"], '%H:%M').time()
                    fin2 = datetime.strptime(turno["fin2"], '%H:%M').time()
                else:
                    inicio2 = None
                    fin2 = None

                for asistencia in nuevas_asistencias:
                    entrada = asistencia["entrada"]

                    dia_asistencia = entrada.strftime("%A").lower()
                    dia_asistencia = utils.traducir_dia(dia_asistencia)

                    # Verifica si el día de la asistencia está programado para trabajar
                    if dias_trabajados.get(dia_asistencia) == "true":
                        # Ahora, verifica si la asistencia se registra en ese día
                        if dia_asistencia == "lunes" and turno["dias_trabajados"].get("lunes") == "true":
                            if inicio1 <= entrada.time() <= fin1:

                                atraso = entrada - \
                                    datetime.combine(entrada.date(), inicio1)
                                if atraso.total_seconds() > 300:
                                    atrasos.append(asistencia)

                            if inicio2 and fin2:
                                if inicio2 <= entrada.time() <= fin2:

                                    atraso = entrada - \
                                        datetime.combine(
                                            entrada.date(), inicio2)
                                    if atraso.total_seconds() > 300:
                                        atrasos.append(asistencia)
                        elif dia_asistencia == "martes" and turno["dias_trabajados"].get("martes") == "true":
                            if inicio1 <= entrada.time() <= fin1:

                                atraso = entrada - \
                                    datetime.combine(entrada.date(), inicio1)
                                if atraso.total_seconds() > 300:
                                    atrasos.append(asistencia)

                            if inicio2 and fin2:
                                if inicio2 <= entrada.time() <= fin2:

                                    atraso = entrada - \
                                        datetime.combine(
                                            entrada.date(), inicio2)
                                    if atraso.total_seconds() > 300:
                                        atrasos.append(asistencia)
                        if dia_asistencia == "miercoles" and turno["dias_trabajados"].get("miercoles") == "true":
                            if inicio1 <= entrada.time() <= fin1:

                                atraso = entrada - \
                                    datetime.combine(entrada.date(), inicio1)
                                if atraso.total_seconds() > 300:
                                    atrasos.append(asistencia)

                            if inicio2 and fin2:
                                if inicio2 <= entrada.time() <= fin2:

                                    atraso = entrada - \
                                        datetime.combine(
                                            entrada.date(), inicio2)
                                    if atraso.total_seconds() > 300:
                                        atrasos.append(asistencia)
                        elif dia_asistencia == "jueves" and turno["dias_trabajados"].get("jueves") == "true":
                            if inicio1 <= entrada.time() <= fin1:

                                atraso = entrada - \
                                    datetime.combine(entrada.date(), inicio1)
                                if atraso.total_seconds() > 300:
                                    atrasos.append(asistencia)

                            if inicio2 and fin2:
                                if inicio2 <= entrada.time() <= fin2:

                                    atraso = entrada - \
                                        datetime.combine(
                                            entrada.date(), inicio2)
                                    if atraso.total_seconds() > 300:
                                        atrasos.append(asistencia)
                        if dia_asistencia == "viernes" and turno["dias_trabajados"].get("viernes") == "true":
                            if inicio1 <= entrada.time() <= fin1:

                                atraso = entrada - \
                                    datetime.combine(entrada.date(), inicio1)
                                if atraso.total_seconds() > 300:
                                    atrasos.append(asistencia)

                            if inicio2 and fin2:
                                if inicio2 <= entrada.time() <= fin2:

                                    atraso = entrada - \
                                        datetime.combine(
                                            entrada.date(), inicio2)
                                    if atraso.total_seconds() > 300:
                                        atrasos.append(asistencia)
                        elif dia_asistencia == "sabado" and turno["dias_trabajados"].get("sabado") == "true":
                            if inicio1 <= entrada.time() <= fin1:

                                atraso = entrada - \
                                    datetime.combine(entrada.date(), inicio1)
                                if atraso.total_seconds() > 300:
                                    atrasos.append(asistencia)

                            if inicio2 and fin2:
                                if inicio2 <= entrada.time() <= fin2:

                                    atraso = entrada - \
                                        datetime.combine(
                                            entrada.date(), inicio2)
                                    if atraso.total_seconds() > 300:
                                        atrasos.append(asistencia)
                        elif dia_asistencia == "domingo" and turno["dias_trabajados"].get("domingo") == "true":
                            if inicio1 <= entrada.time() <= fin1:

                                atraso = entrada - \
                                    datetime.combine(entrada.date(), inicio1)
                                if atraso.total_seconds() > 300:
                                    atrasos.append(asistencia)

                            if inicio2 and fin2:
                                if inicio2 <= entrada.time() <= fin2:

                                    atraso = entrada - \
                                        datetime.combine(
                                            entrada.date(), inicio2)
                                    if atraso.total_seconds() > 300:
                                        atrasos.append(asistencia)

        return {"error": "N", "mensaje": "", "objetos": atrasos}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.get("/obtener_asistencias")
async def obtener_asistencias(request: Request, usuario_codigo, fecha_desde, fecha_hasta, numero_de_pagina, registros_por_pagina):
    offset = (int(numero_de_pagina) - 1) * int(registros_por_pagina)

    fecha_hasta = datetime.strptime(fecha_hasta, '%Y/%m/%d')
    fecha_hasta = fecha_hasta + timedelta(days=1) - timedelta(seconds=1)

    query = f"SELECT tasistencias.codigo, templeado.nombres || ' ' || templeado.apellidos AS nombre_completo, talmacen.alm_nomcom as lugar_asignado, entrada, salida FROM rol.tasistencias INNER JOIN rol.templeado ON tasistencias.usuario_codigo = templeado.codigo INNER JOIN rol.tlugaresasignados ON tasistencias.usuario_codigo = tlugaresasignados.usuario_codigo INNER JOIN rol.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN comun.talmacen ON talmacen.alm_codigo = tcoordenadas.alm_codigo WHERE tasistencias.usuario_codigo = {usuario_codigo} AND entrada BETWEEN '{fecha_desde}' AND '{fecha_hasta}' ORDER BY entrada OFFSET {offset} ROWS FETCH FIRST {registros_por_pagina} ROWS ONLY"

    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 832, 1)

    if acceso[0]['tiene_acceso'] != '':
        return {
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }

    try:
        token_middleware.verify_token(token)
        with Session(engine) as session:
            rows = session.execute(text(query)).fetchall()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": "",
                    "objetos": rows,
                }
            asistencias = [row._asdict() for row in rows]

            excepciones = await excepciones_autorizadas(usuario_codigo)

            nuevas_asistencias = []
            for diccionario in asistencias:
                fecha = diccionario['entrada'].strftime('%Y/%m/%d')
                if fecha not in excepciones:
                    nuevas_asistencias.append(diccionario)

            return {"error": "N", "mensaje": "", "objetos": nuevas_asistencias}

    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


async def empleados_asignados(lugar: str):
    sql = "SELECT templeado.codigo, templeado.nombres || ' ' || templeado.apellidos AS nombre_completo, talmacen.alm_nomcom FROM rol.tlugaresasignados INNER JOIN rol.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN comun.talmacen ON talmacen.alm_codigo = tcoordenadas.alm_codigo INNER JOIN rol.templeado ON tlugaresasignados.usuario_codigo = templeado.codigo"
    if lugar not in [None, '', 'N']:
        sql += f" WHERE talmacen.alm_nomcom LIKE '{lugar}'"

    sql += " ORDER BY nombre_completo"

    with Session(engine) as session:
        rows = session.execute(text(sql)).fetchall()
        objetos = [row._asdict() for row in rows]
        return objetos


async def excepciones_autorizadas(codigo: int):
    sql = f"SELECT usuario_codigo, dias FROM rol.texcepciones WHERE usuario_codigo = {codigo} AND autorizado = true;"

    with Session(engine) as session:
        rows = session.execute(text(sql)).fetchall()
        objetos = [row._asdict() for row in rows]
        dias_list = [d['dias'] for d in objetos]
        dias_flat = [date for sublist in dias_list for date in sublist]
        return dias_flat


async def empleados_asistencias():
    sql = "SELECT usuario_codigo FROM rol.tasistencias ORDER BY usuario_codigo"
    with Session(engine) as session:
        rows = session.execute(text(sql)).fetchall()
        objetos = [row._asdict() for row in rows]
        return objetos


async def calcular_suplementarias(usuario_codigo, fecha_desde, fecha_hasta):
    sql = f"SELECT SUM(horas) FROM rol.thoras_suplementarias WHERE usuario_codigo = {usuario_codigo} AND fecha BETWEEN '{fecha_desde}' AND '{fecha_hasta}'"
    with Session(engine) as session:
        rows = session.execute(text(sql)).fetchall()
        objetos = [row._asdict() for row in rows]
        return objetos[0]['sum']


async def calcular(usuario_codigo, fecha_desde, fecha_hasta):

    fecha_hasta = datetime.strptime(unquote(fecha_hasta), '%Y/%m/%d')
    fecha_hasta = fecha_hasta + timedelta(days=1) - timedelta(seconds=1)
    query = f"SELECT entrada, salida FROM rol.tasistencias WHERE usuario_codigo = {usuario_codigo} AND entrada BETWEEN '{unquote(fecha_desde)}' AND '{fecha_hasta}'"

    excepciones = await excepciones_autorizadas(usuario_codigo)

    with Session(engine) as session:
        rows = session.execute(text(query)).fetchall()
        if len(rows) == 0:
            return {
                "error": "S",
                "mensaje": "",
                "objetos": rows,
            }

        asistencias = [row._asdict() for row in rows]

        nuevas_asistencias = []

        for diccionario in asistencias:
            fecha = diccionario['entrada'].strftime('%Y/%m/%d')
            if fecha not in excepciones:
                nuevas_asistencias.append(diccionario)

    query = f"SELECT tturnos.dias_trabajados, tturnos.inicio1, tturnos.fin1, tturnos.inicio2, tturnos.fin2 FROM rol.tlugaresasignados INNER JOIN rol.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN rol.templeado ON tlugaresasignados.usuario_codigo = templeado.codigo INNER JOIN rol.tturnosasignados ON tturnosasignados.usuario_codigo = tlugaresasignados.usuario_codigo INNER JOIN rol.tturnos ON tturnosasignados.turno_codigo = tturnos.codigo WHERE templeado.codigo = {usuario_codigo}"

    horarios = await get_horarios(usuario_codigo)

    turnos = []

    for horario in horarios:
        info = await get_horario_info(horario)
        turnos.append(info[0])

    horas_trabajadas = 0
    atrasos = 0

    for turno in turnos:
        dias_trabajados = turno["dias_trabajados"]

        if isinstance(dias_trabajados, list):
            inicio1 = datetime.strptime(turno["inicio1"], '%H:%M').time()
            fin1 = datetime.strptime(turno["fin1"], '%H:%M').time()
            if turno["inicio2"] and turno["fin2"]:
                inicio2 = datetime.strptime(
                    turno["inicio2"], '%H:%M').time()
                fin2 = datetime.strptime(turno["fin2"], '%H:%M').time()
            else:
                inicio2 = None
                fin2 = None

            for asistencia in nuevas_asistencias:
                for rango in dias_trabajados:
                    entrada = asistencia["entrada"]
                    salida = asistencia["salida"]

                    fecha_inicio = datetime.strptime(
                        rango["from"], "%Y/%m/%d")
                    fecha_fin = datetime.strptime(
                        rango["to"], "%Y/%m/%d") + timedelta(days=1) - timedelta(seconds=1)

                    if fecha_inicio <= entrada <= fecha_fin:

                        horas_trabajadas += utils.calcular_horas(
                            inicio1, fin1, inicio2, fin2, entrada, salida)
                        atrasos += utils.calcular_atrasos(
                            inicio1, fin1, inicio2, fin2, entrada, salida)

        else:
            inicio1 = datetime.strptime(turno["inicio1"], '%H:%M').time()
            fin1 = datetime.strptime(turno["fin1"], '%H:%M').time()
            if turno["inicio2"] and turno["fin2"]:
                inicio2 = datetime.strptime(
                    turno["inicio2"], '%H:%M').time()
                fin2 = datetime.strptime(turno["fin2"], '%H:%M').time()
            else:
                inicio2 = None
                fin2 = None

            for asistencia in nuevas_asistencias:
                entrada = asistencia["entrada"]
                salida = asistencia["salida"]

                dia_asistencia = entrada.strftime("%A").lower()
                dia_asistencia = utils.traducir_dia(dia_asistencia)

                # Verifica si el día de la asistencia está programado para trabajar
                if dias_trabajados.get(dia_asistencia) == "true":
                    # Ahora, verifica si la asistencia se registra en ese día
                    if dia_asistencia == "lunes" and turno["dias_trabajados"].get("lunes") == "true":
                        horas_trabajadas += utils.calcular_horas(
                            inicio1, fin1, inicio2, fin2, entrada, salida)
                        atrasos += utils.calcular_atrasos(
                            inicio1, fin1, inicio2, fin2, entrada, salida)
                    elif dia_asistencia == "martes" and turno["dias_trabajados"].get("martes") == "true":
                        horas_trabajadas += utils.calcular_horas(
                            inicio1, fin1, inicio2, fin2, entrada, salida)
                        atrasos += utils.calcular_atrasos(
                            inicio1, fin1, inicio2, fin2, entrada, salida)
                    if dia_asistencia == "miercoles" and turno["dias_trabajados"].get("miercoles") == "true":
                        horas_trabajadas += utils.calcular_horas(
                            inicio1, fin1, inicio2, fin2, entrada, salida)
                        atrasos += utils.calcular_atrasos(
                            inicio1, fin1, inicio2, fin2, entrada, salida)
                    elif dia_asistencia == "jueves" and turno["dias_trabajados"].get("jueves") == "true":
                        horas_trabajadas += utils.calcular_horas(
                            inicio1, fin1, inicio2, fin2, entrada, salida)
                        atrasos += utils.calcular_atrasos(
                            inicio1, fin1, inicio2, fin2, entrada, salida)
                    if dia_asistencia == "viernes" and turno["dias_trabajados"].get("viernes") == "true":
                        horas_trabajadas += utils.calcular_horas(
                            inicio1, fin1, inicio2, fin2, entrada, salida)
                        atrasos += utils.calcular_atrasos(
                            inicio1, fin1, inicio2, fin2, entrada, salida)
                    elif dia_asistencia == "sabado" and turno["dias_trabajados"].get("sabado") == "true":
                        horas_trabajadas += utils.calcular_horas(
                            inicio1, fin1, inicio2, fin2, entrada, salida)
                        atrasos += utils.calcular_atrasos(
                            inicio1, fin1, inicio2, fin2, entrada, salida)
                    elif dia_asistencia == "domingo" and turno["dias_trabajados"].get("domingo") == "true":
                        horas_trabajadas += utils.calcular_horas(
                            inicio1, fin1, inicio2, fin2, entrada, salida)
                        atrasos += utils.calcular_atrasos(
                            inicio1, fin1, inicio2, fin2, entrada, salida)

    return {
        "horas_trabajadas": round(horas_trabajadas, 2),
        "atrasos": round(atrasos, 2),
    }


async def get_horarios(codigo: int):
    sql = f"SELECT DISTINCT horarios FROM rol.tasistencias WHERE usuario_codigo = {codigo}"
    with Session(engine) as session:
        rows = session.execute(text(sql)).fetchall()
        objetos = [row._asdict() for row in rows]
        horarios = [objeto['turno_codigo']
                    for objeto in objetos[0]['horarios']]

        return horarios


@router.get('/verificar_horarios_asignados')
async def verificar_horarios_asignados(request: Request, codigo: int):
    token = request.headers.get('token')
    sql = f"SELECT DISTINCT usuario_codigo FROM rol.tasistencias"
    try:
        token_middleware.verify_token(token)
        with Session(engine) as session:
            rows = session.execute(text(sql)).fetchall()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": "",
                    "objetos": False,
                }
            codigos = [row._asdict() for row in rows]
            valores = [d['usuario_codigo'] for d in codigos]

            nuevos_valores = []
            for valor in valores:
                nuevo_valor = await get_horarios(valor)
                nuevos_valores.append(nuevo_valor)

            codigos = [
                numero for sublista in nuevos_valores for numero in sublista]	

            horario_asignado = False
            if (codigo in codigos):
                horario_asignado = True		
		
            #     nuevos_valores.append(get_horarios(valor))
            return {"error": "N", "mensaje": "", "objetos": horario_asignado}

    except Exception as e:
        return {"error": "S", "mensaje": str(e), "objetos": horario_asignado}


async def get_horario_info(codigo: int):
    sql = f"SELECT dias_trabajados, inicio1, fin1, inicio2, fin2 FROM rol.tturnos WHERE codigo = {codigo}"
    with Session(engine) as session:
        rows = session.execute(text(sql)).fetchall()
        return rows


@router.get("/calcular_horas_atrasos")
async def calcular_horas_atrasos(request: Request, lugar: str, fecha_desde: str, fecha_hasta: str):
    token = request.headers.get('token')

    try:
        token_middleware.verify_token(token)
        with Session(engine) as session:
            employees = await empleados_asignados(lugar)
            codigos = await empleados_asistencias()

            # Extraer valores únicos de 'usuario_codigo'
            unique_user_codes = set(codigo['usuario_codigo']
                                    for codigo in codigos)

            user_codes = list(unique_user_codes)

            empleados = [
                employee for employee in employees if employee['codigo'] in user_codes]

            for empleado in empleados:

                calculos = await calcular(empleado['codigo'], fecha_desde, fecha_hasta)

                calculos_suplementarias = await calcular_suplementarias(empleado['codigo'], fecha_desde, fecha_hasta)

                empleado['horas_trabajadas'] = calculos['horas_trabajadas']
                empleado['atrasos'] = calculos['atrasos']
                empleado['horas_suplementarias'] = calculos_suplementarias

            return {"error": "N", "mensaje": "", "objetos": empleados}

    except Exception as error:
        return {"error": "S", "mensaje": str(error)}
