from datetime import datetime, timedelta
from datetime import time
from urllib.parse import unquote
import json
import math
import unicodedata
import fastapi
import locale
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


@router.post("/registrar_entrada")
async def registrar_entrada(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    employee_id = data['employee_id']

    sql = f"INSERT INTO comun.tasistencias (usuario_codigo, entrada) VALUES ({employee_id}, NOW()) RETURNING codigo"

    try:

        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Registro de entrada exitoso", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.put("/registrar_salida")
async def registrar_salida(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    employee_id = data['employee_id']

    sql = f"UPDATE comun.tasistencias SET salida = NOW() WHERE codigo = (SELECT codigo FROM comun.tasistencias WHERE usuario_codigo = {employee_id} ORDER BY entrada DESC LIMIT 1) AND salida IS NULL RETURNING codigo"

    try:
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Registro de salida exitoso", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.get("/obtener_numero_paginas")
async def obtener_numero_paginas(request: Request, usuario_codigo, fecha_desde, fecha_hasta):
    token = request.headers.get('token')
    sql = f"SELECT COUNT(*) FROM comun.tasistencias WHERE usuario_codigo = {usuario_codigo} AND entrada BETWEEN '{fecha_desde}' AND '{fecha_hasta}'"

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

            return {"error": "N", "mensaje": "", "objetos": rows[0][0]}

    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.get("/obtener_asistencias")
async def obtener_asistencias(request: Request, usuario_codigo, fecha_desde, fecha_hasta, numero_de_pagina, registros_por_pagina):
    token = request.headers.get('token')
    offset = (int(numero_de_pagina) - 1) * int(registros_por_pagina)

    fecha_hasta = datetime.strptime(fecha_hasta, '%Y/%m/%d')
    fecha_hasta = fecha_hasta + timedelta(days=1) - timedelta(seconds=1)

    query = f"SELECT tasistencias.codigo, templeado.nombres || ' ' || templeado.apellidos AS nombre_completo, talmacen.alm_nomcom as lugar_asignado, entrada, salida FROM comun.tasistencias INNER JOIN rol.templeado ON tasistencias.usuario_codigo = templeado.codigo INNER JOIN comun.tlugaresasignados ON tasistencias.usuario_codigo = tlugaresasignados.usuario_codigo INNER JOIN comun.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN comun.talmacen ON talmacen.alm_codigo = tcoordenadas.alm_codigo WHERE tasistencias.usuario_codigo = {usuario_codigo} AND entrada BETWEEN '{fecha_desde}' AND '{fecha_hasta}' ORDER BY entrada OFFSET {offset} ROWS FETCH FIRST {registros_por_pagina} ROWS ONLY"

    try:
        if not utils.verify_token(token):
            raise HTTPException(
                status_code=401, detail="Usuario no autorizado")
        with Session(engine2) as session:
            rows = session.execute(text(query)).fetchall()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": "",
                    "objetos": rows,
                }
            asistencias = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": asistencias}

    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.get("/calcular_horas_atrasos")
async def calcular_horas_atrasos(request: Request, usuario_codigo, fecha_desde, fecha_hasta):
    token = request.headers.get('token')
    fecha_desde = unquote(fecha_desde)
    fecha_hasta = unquote(fecha_hasta)
    # query = f"SELECT entrada, salida FROM comun.tasistencias WHERE usuario_codigo = {usuario_codigo} AND EXTRACT(MONTH FROM entrada) = {mes}"
    # Agregar un día a la fecha hasta y restar un segundo
    fecha_hasta = datetime.strptime(fecha_hasta, '%Y/%m/%d')
    fecha_hasta = fecha_hasta + timedelta(days=1) - timedelta(seconds=1)
    query = f"SELECT entrada, salida FROM comun.tasistencias WHERE usuario_codigo = {usuario_codigo} AND entrada BETWEEN '{fecha_desde}' AND '{fecha_hasta}'"

    try:
        if not utils.verify_token(token):
            raise HTTPException(
                status_code=401, detail="Usuario no autorizado")
        with Session(engine2) as session:
            rows = session.execute(text(query)).fetchall()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": "",
                    "objetos": rows,
                }

            asistencias = [row._asdict() for row in rows]

        query = f"SELECT tturnos.dias_trabajados, tturnos.inicio1, tturnos.fin1, tturnos.inicio2, tturnos.fin2 FROM comun.tlugaresasignados INNER JOIN comun.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN rol.templeado ON tlugaresasignados.usuario_codigo = templeado.codigo INNER JOIN comun.tturnosasignados ON tturnosasignados.usuario_codigo = tlugaresasignados.usuario_codigo INNER JOIN comun.tturnos ON tturnosasignados.turno_codigo = tturnos.codigo WHERE templeado.codigo = {usuario_codigo}"

        with Session(engine2) as session:
            turnos = session.execute(text(query)).fetchall()

            if len(turnos) == 0:
                return {
                    "error": "S",
                    "mensaje": "",
                    "objetos": turnos,
                }

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

                for asistencia in asistencias:
                    entrada = asistencia["entrada"]
                    salida = asistencia["salida"]

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

                for asistencia in asistencias:
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

    except Exception as error:
        return {"error": "S", "mensaje": str(error)}
