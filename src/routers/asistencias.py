from datetime import datetime, timedelta
from datetime import time
from urllib.parse import unquote
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


async def horarios_asignados(codigo: int):
    sql = f"SELECT turno_codigo FROM comun.tturnosasignados WHERE usuario_codigo = {codigo}"
    with Session(engine2) as session:
        rows = session.execute(text(sql)).fetchall()
        objetos = [row._asdict() for row in rows]
        return objetos


async def lugar_asignado(codigo: int):
    sql = f"SELECT coordenadas_codigo FROM comun.tlugaresasignados WHERE usuario_codigo = {codigo}"
    with Session(engine2) as session:
        rows = session.execute(text(sql)).fetchall()
        objetos = [row._asdict() for row in rows]
        return objetos


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

    sql = f"INSERT INTO comun.tasistencias (usuario_codigo, entrada, horarios, lugar_asignado) VALUES ({employee_id}, NOW(), '{json.dumps(horarios)}', {lugar[0]['coordenadas_codigo']}) RETURNING codigo"

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


@router.get("/obtener_atrasos")
async def obtener_atrasos(request: Request, usuario_codigo, fecha_desde, fecha_hasta):
    token = request.headers.get('token')

    fecha_hasta = datetime.strptime(fecha_hasta, '%Y/%m/%d')
    fecha_hasta = fecha_hasta + timedelta(days=1) - timedelta(seconds=1)

    query = f"SELECT tasistencias.codigo, templeado.nombres || ' ' || templeado.apellidos AS nombre_completo, talmacen.alm_nomcom as lugar_asignado, entrada, salida FROM comun.tasistencias INNER JOIN rol.templeado ON tasistencias.usuario_codigo = templeado.codigo INNER JOIN comun.tlugaresasignados ON tasistencias.usuario_codigo = tlugaresasignados.usuario_codigo INNER JOIN comun.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN comun.talmacen ON talmacen.alm_codigo = tcoordenadas.alm_codigo WHERE tasistencias.usuario_codigo = {usuario_codigo} AND entrada BETWEEN '{fecha_desde}' AND '{fecha_hasta}' ORDER BY entrada"

    with Session(engine2) as session:
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

    sql = f"SELECT tturnos.dias_trabajados, tturnos.inicio1, tturnos.fin1, tturnos.inicio2, tturnos.fin2 FROM comun.tlugaresasignados INNER JOIN comun.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN rol.templeado ON tlugaresasignados.usuario_codigo = templeado.codigo INNER JOIN comun.tturnosasignados ON tturnosasignados.usuario_codigo = tlugaresasignados.usuario_codigo INNER JOIN comun.tturnos ON tturnosasignados.turno_codigo = tturnos.codigo WHERE templeado.codigo = {usuario_codigo}"

    try:
        if not utils.verify_token(token):
            raise HTTPException(
                status_code=401, detail="Usuario no autorizado")

        with Session(engine2) as session:
            turnos = session.execute(text(sql)).fetchall()

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
    sql = "SELECT templeado.codigo, templeado.nombres || ' ' || templeado.apellidos AS nombre_completo, talmacen.alm_nomcom FROM comun.tlugaresasignados INNER JOIN comun.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN comun.talmacen ON talmacen.alm_codigo = tcoordenadas.alm_codigo INNER JOIN rol.templeado ON tlugaresasignados.usuario_codigo = templeado.codigo"
    if lugar not in [None, '', 'N']:
        sql += f" WHERE talmacen.alm_nomcom LIKE '{lugar}'"

    sql += " ORDER BY nombre_completo"

    with Session(engine2) as session:
        rows = session.execute(text(sql)).fetchall()
        objetos = [row._asdict() for row in rows]
        return objetos


async def excepciones_autorizadas(codigo: int):
    sql = f"SELECT usuario_codigo, dias FROM comun.texcepciones WHERE usuario_codigo = {codigo} AND autorizado = true;"

    with Session(engine2) as session:
        rows = session.execute(text(sql)).fetchall()
        objetos = [row._asdict() for row in rows]
        dias_list = [d['dias'] for d in objetos]
        dias_flat = [date for sublist in dias_list for date in sublist]
        return dias_flat


async def empleados_asistencias():
    sql = "SELECT usuario_codigo FROM comun.tasistencias ORDER BY usuario_codigo"
    with Session(engine2) as session:
        rows = session.execute(text(sql)).fetchall()
        objetos = [row._asdict() for row in rows]
        return objetos


async def calcular(usuario_codigo, fecha_desde, fecha_hasta):

    fecha_hasta = datetime.strptime(unquote(fecha_hasta), '%Y/%m/%d')
    fecha_hasta = fecha_hasta + timedelta(days=1) - timedelta(seconds=1)
    query = f"SELECT entrada, salida FROM comun.tasistencias WHERE usuario_codigo = {usuario_codigo} AND entrada BETWEEN '{unquote(fecha_desde)}' AND '{fecha_hasta}'"

    excepciones = await excepciones_autorizadas(usuario_codigo)

    with Session(engine2) as session:
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

    query = f"SELECT tturnos.dias_trabajados, tturnos.inicio1, tturnos.fin1, tturnos.inicio2, tturnos.fin2 FROM comun.tlugaresasignados INNER JOIN comun.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN rol.templeado ON tlugaresasignados.usuario_codigo = templeado.codigo INNER JOIN comun.tturnosasignados ON tturnosasignados.usuario_codigo = tlugaresasignados.usuario_codigo INNER JOIN comun.tturnos ON tturnosasignados.turno_codigo = tturnos.codigo WHERE templeado.codigo = {usuario_codigo}"

    horarios = await get_horarios(usuario_codigo)

    print('[HORARIOS]: ', horarios)

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
    sql = f"SELECT DISTINCT horarios FROM comun.tasistencias WHERE usuario_codigo = {codigo}"
    with Session(engine2) as session:
        rows = session.execute(text(sql)).fetchall()
        objetos = [row._asdict() for row in rows]
        horarios = [objeto['turno_codigo']
                    for objeto in objetos[0]['horarios']]

        return horarios


@router.get('/verificar_horarios_asignados')
async def verificar_horarios_asignados(request: Request, codigo: int):
    token = request.headers.get('token')
    sql = f"SELECT DISTINCT usuario_codigo FROM comun.tasistencias"
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
        return {"error": "S", "mensaje": str(e)}


async def get_horario_info(codigo: int):
    sql = f"SELECT dias_trabajados, inicio1, fin1, inicio2, fin2 FROM comun.tturnos WHERE codigo = {codigo}"
    with Session(engine2) as session:
        rows = session.execute(text(sql)).fetchall()
        return rows


@router.get("/calcular_horas_atrasos")
async def calcular_horas_atrasos(request: Request, lugar: str, fecha_desde: str, fecha_hasta: str):
    token = request.headers.get('token')

    try:
        if not utils.verify_token(token):
            raise HTTPException(
                status_code=401, detail="Usuario no autorizado")
        with Session(engine2) as session:
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

                empleado['horas_trabajadas'] = calculos['horas_trabajadas']
                empleado['atrasos'] = calculos['atrasos']

            return {"error": "N", "mensaje": "", "objetos": empleados}

    except Exception as error:
        return {"error": "S", "mensaje": str(error)}

    # # Crear una lista vacía para almacenar los números de turno_codigo
    # turno_codigos = set()

    # # Iterar a través de la lista de objetos y extraer los números de turno_codigo
    # for obj in objetos:
    #     for horario in obj['horarios']:
    #         turno_codigos.add(horario['turno_codigo'])

    # # Convertir el conjunto en una lista
    # horarios = list(turno_codigos)

    # with Session(engine2) as session:
    #     turnos = session.execute(text(query)).fetchall()

    #     if len(turnos) == 0:
    #         return {
    #             "error": "S",
    #             "mensaje": "",
    #             "objetos": turnos,
    #         }

    #     print('[TURNOS]: ', turnos)
