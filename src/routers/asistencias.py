from datetime import datetime
from datetime import time
import json
import math
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


@router.post("/registrar_entrada")
async def registrar_entrada(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    employee_id = data['employee_id']

    print('[EMPLOYEE ID]', employee_id)

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

    print('[EMPLOYEE ID]', employee_id)

    sql = f"UPDATE comun.tasistencias SET salida = NOW() WHERE codigo = (SELECT codigo FROM comun.tasistencias WHERE usuario_codigo = {employee_id} ORDER BY entrada DESC LIMIT 1) AND salida IS NULL RETURNING codigo"

    try:
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Registro de salida exitoso", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.get("/calcular_horas_atrasos")
async def calcular_horas_atrasos(request: Request, usuario_codigo, mes):
    token = request.headers.get('token')

    query = f"SELECT entrada, salida FROM comun.tasistencias WHERE usuario_codigo = {usuario_codigo} AND EXTRACT(MONTH FROM entrada) = {mes}"

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

        query = f"SELECT tturnos.inicio1, tturnos.fin1, tturnos.inicio2, tturnos.fin2 FROM comun.tlugaresasignados INNER JOIN comun.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN rol.templeado ON tlugaresasignados.usuario_codigo = templeado.codigo INNER JOIN comun.tturnosasignados ON tturnosasignados.usuario_codigo = tlugaresasignados.usuario_codigo INNER JOIN comun.tturnos ON tturnosasignados.turno_codigo = tturnos.codigo WHERE templeado.codigo = {usuario_codigo}"

        with Session(engine2) as session:
            turnos = session.execute(text(query)).fetchall()
            print('[TURNOS]: ', turnos)
            if len(turnos) == 0:
                return {
                    "error": "S",
                    "mensaje": "",
                    "objetos": turnos,
                }

        horas_trabajadas = 0
        atrasos = 0

        for turno in turnos:
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

                # Verifica si la asistencia está dentro de la primera jornada
                if inicio1 <= entrada.time() <= fin1:
                    # Calcula las horas trabajadas en la primera jornada
                    if salida:
                        horas_trabajadas += (salida - entrada).seconds / 3600

                    # Calcula el atraso (si hay)
                    atraso = entrada - \
                        datetime.combine(entrada.date(), inicio1)
                    if atraso.total_seconds() > 300:  # 300 segundos = 5 minutos
                        atrasos += atraso.total_seconds() / 60

                if inicio2 and fin2:
                    # Verifica si la asistencia está dentro de la segunda jornada
                    if inicio2 <= entrada.time() <= fin2:
                        # Calcula las horas trabajadas en la segunda jornada
                        if salida:
                            horas_trabajadas += (salida -
                                                 entrada).seconds / 3600

                        # Calcula el atraso (si hay)
                        atraso = entrada - \
                            datetime.combine(entrada.date(), inicio2)
                        if atraso.total_seconds() > 300:  # 300 segundos = 5 minutos
                            atrasos += atraso.total_seconds() / 60

        return {
            "horas_trabajadas": round(horas_trabajadas, 2)/2,
            "atrasos": round(atrasos, 2)/2,
        }

    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


# @router.get("/calcular_horas_atrasos")
# async def calcular_horas_atrasos(request: Request, usuario_codigo, mes):
    token = request.headers.get('token')

    query = f"SELECT entrada, salida FROM comun.tasistencias WHERE usuario_codigo = {usuario_codigo} AND EXTRACT(MONTH FROM entrada) = {mes}"

    print('[QUERY]: ', query)

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

            print('[ASISTENCIAS]: ', asistencias)

        query = f"SELECT tturnos.inicio1, tturnos.fin1, tturnos.inicio2, tturnos.fin2 FROM comun.tlugaresasignados INNER JOIN comun.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN rol.templeado ON tlugaresasignados.usuario_codigo = templeado.codigo INNER JOIN comun.tturnosasignados ON tturnosasignados.usuario_codigo = tlugaresasignados.usuario_codigo INNER JOIN comun.tturnos ON tturnosasignados.turno_codigo = tturnos.codigo WHERE templeado.codigo = {usuario_codigo}"

        print('[NEW QUERY]: ', query)

        with Session(engine2) as session:
            turnos = session.execute(text(query)).fetchall()
            print('[TURNOS]: ', turnos)
            if len(turnos) == 0:
                return {
                    "error": "S",
                    "mensaje": "",
                    "objetos": turnos,
                }

        horas_trabajadas = 0
        atrasos = 0

        for turno in turnos:
            for asistencia in asistencias:
                entrada = asistencia["entrada"]
                salida = asistencia["salida"]
                inicio1 = time.fromisoformat(turno["inicio1"])
                fin1 = time.fromisoformat(turno["fin1"])
                inicio2 = turno["inicio2"]
                fin2 = turno["fin2"]

                # Verifica si el usuario tiene dos jornadas

                # Verifica si la asistencia está dentro de la primera jornada
                if inicio1 <= entrada.time() <= fin1:
                    # Calcula las horas trabajadas en la primera jornada
                    print('[SALIDA]: ', salida)
                    if salida:
                        horas_trabajadas += (salida - entrada).seconds / 3600
                        print('[HORAS TRABAJADAS]: ', horas_trabajadas)

                # Calcula el atraso (si hay)
                atraso = entrada.time() - inicio1
                if atraso.total_seconds() > 300:  # 300 segundos = 5 minutos
                    atrasos += atraso.total_seconds() / 60

                if inicio2 and fin2:
                    # Verifica si la asistencia está dentro de la segunda jornada
                    if inicio2 <= entrada.time() <= fin2:
                        print('inicio2 <= entrada <= fin2')
                        # Calcula las horas trabajadas en la segunda jornada
                        if salida:
                            horas_trabajadas += (salida -
                                                 entrada).seconds / 3600
                            print('[HORAS TRABAJADAS]: ', horas_trabajadas)

                # Calcula el atraso (si hay)
                atraso = entrada.time() - inicio1
                if atraso.total_seconds() > 300:  # 300 segundos = 5 minutos
                    atrasos += atraso.total_seconds() / 60

        return {
            "horas_trabajadas": round(horas_trabajadas, 2),
            "atrasos": round(atrasos, 2),
        }

    except Exception as error:
        return {"error": "S", "mensaje": str(error)}
