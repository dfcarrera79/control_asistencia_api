import os
import json
import shutil
import fastapi
from PIL import Image
from src.utils import utils
from src.config import config
from pydantic import BaseModel
from urllib.parse import unquote
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from fastapi import Request, UploadFile, File
from datetime import datetime, timedelta, time
from src.routers.controllers import SessionHandler
from src.middleware import token_middleware, acceso_middleware

# Models
class RegistrarModel(BaseModel):
    filepath: str
    codigo: int


# Establish connections to PostgreSQL databases for "apromed"
engine = create_engine(config.db_uri)

# Crear una instancia de la clase con tu motor de base de datos
query_handler = SessionHandler(engine)

# API Route Definitions
router = fastapi.APIRouter()

async def horarios_asignados(codigo: int):
    mes_actual = datetime.now().month
    sql = f"SELECT codigo FROM rol.thorariosasignados WHERE usuario_codigo = {codigo} AND mes = {mes_actual}"
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


@router.put("/actualizar_suplementarias")
async def actualizar__suplementarias(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 831, 3)
    
    auditoria_text = f"usuario: {data['usuario']}\nfecha: {data['fecha']}\nhoras: {data['horas']}\nregistro_eliminado_por: {data['asignado_por']}"
    
    sql = f"""
    UPDATE rol.thoras_suplementarias
    SET usuario_codigo = NULL, fecha = NULL, horas = NULL, asignado_por = NULL, 
        auditoria = CASE 
                        WHEN auditoria IS NULL THEN ''
                        ELSE auditoria || '\n-------\n'
                    END || '{auditoria_text}'
    WHERE codigo = {data['codigo']} RETURNING codigo;
    """
    
    return query_handler.execute_sql_token(sql, token, "Registro eliminado con éxito.") 


@router.get("/obtener_registros_suplementarias")
async def obtener_registros_suplementarias(request: Request, departamento: str, desde: str, hasta: str):
    sql = "SELECT COUNT(*) AS total FROM rol.thoras_suplementarias TS INNER JOIN rol.TEmpleado TEmpleado ON TS.usuario_codigo = TEmpleado.codigo INNER JOIN usuario.TUsuario TUsuario ON TS.asignado_por = TUsuario.usu_codigo INNER JOIN rol.TPlantillaRol ON TEmpleado.codigo_plantilla = TPlantillaRol.codigo"
    token = request.headers.get('token')
    
    condiciones = utils.construir_condiciones_where(departamento, desde, hasta)
    
    if condiciones:
        sql += " WHERE " + " AND ".join(condiciones) 
        
    return query_handler.execute_sql_token(sql, token, "")


@router.get("/obtener_horas_suplementarias")
async def obtener_horas_suplementarias(request: Request, departamento, desde: str, hasta: str, numeroDePagina: int, registrosPorPagina: int):
    offset = (numeroDePagina - 1) * registrosPorPagina
    token = request.headers.get('token')
    sql = "SELECT TS.codigo, TEmpleado.nombres || ' ' || TEmpleado.apellidos AS nombre_completo_usuario, TPlantillaRol.descripcion AS departamento, TS.fecha, TS.horas, TUsuario.usu_nomape AS asignado_por FROM rol.thoras_suplementarias TS INNER JOIN rol.TEmpleado TEmpleado ON TS.usuario_codigo = TEmpleado.codigo INNER JOIN usuario.TUsuario TUsuario ON TS.asignado_por = TUsuario.usu_codigo INNER JOIN rol.TPlantillaRol ON TEmpleado.codigo_plantilla = TPlantillaRol.codigo"
  
    condiciones = utils.construir_condiciones_where(departamento, desde, hasta)
    
    if condiciones:
        sql += " WHERE " + " AND ".join(condiciones)
        
    sql += f" ORDER BY codigo DESC OFFSET {offset} ROWS FETCH FIRST {registrosPorPagina} ROWS ONLY"    
    
    return query_handler.execute_sql_token(sql, token, "")


@router.get("/obtener_entrada_registrada")
async def obtener_entrada_registrada(codigo: int, fecha: str):
    sql = f"SELECT codigo, jornada FROM rol.tasistencias WHERE usuario_codigo = {codigo} AND DATE(entrada) = '{fecha}'"
    return query_handler.execute_sql(sql, "")


@router.get("/obtener_salida_registrada")
async def obtener_salida_registrada(codigo: int, fecha: str, jornada: int):
    sql = f"SELECT codigo FROM rol.tasistencias WHERE usuario_codigo = {codigo} AND DATE(salida) = '{fecha}' AND jornada = {jornada}"
    return query_handler.execute_sql(sql, "")


@router.get("/obtener_asistencias_fecha")
async def obtener_asistencias_fecha(request: Request, codigo: int, fecha: str):
    token = request.headers.get('token')
    sql = f"SELECT entrada, salida FROM rol.tasistencias WHERE usuario_codigo = {codigo} AND DATE(entrada) = '{fecha}'"
    return query_handler.execute_sql_token(sql, token, "")

@router.get("/modificar_horario_dia")
async def modificar_horario_dia(request: Request):
    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 827, 1)
    if acceso[0]['tiene_acceso'] != '':
        return {
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }
        
    return {
        "error": "N",
        "mensaje": "",
        "objetos": True,
    }    

@router.get("/obtener_asistencias_por_fecha")
async def obtener_asistencias_por_fecha(codigo: int, fecha: str):
    # Convertir la fecha proporcionada en un objeto datetime
    fecha_obj = datetime.strptime(fecha, "%Y-%m-%d")
    
    # Calcular el inicio de la semana (lunes)
    inicio_semana = fecha_obj - timedelta(days=fecha_obj.weekday())
    
    # Calcular el final de la semana (domingo)
    fin_semana = inicio_semana + timedelta(days=6)
    
    # Convertir las fechas de nuevo a formato string
    inicio_semana_str = inicio_semana.strftime("%Y-%m-%d")
    fin_semana_str = fin_semana.strftime("%Y-%m-%d")
    
    # Modificar la consulta SQL para que busque dentro del rango de fechas
    sql = f"SELECT t.entrada, t.salida, s.horas FROM rol.tasistencias t LEFT JOIN rol.thoras_suplementarias s ON t.usuario_codigo = s.usuario_codigo AND DATE(t.entrada) = s.fecha WHERE t.usuario_codigo = {codigo} AND DATE(t.entrada) BETWEEN '{inicio_semana_str}' AND '{fin_semana_str}' ORDER BY t.codigo;"
    
    return query_handler.execute_sql(sql, "")


@router.post("/registrar_entrada")
async def registrar_entrada(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    horarios = await horarios_asignados(data['employee_id'])

    if len(horarios) == 0:
        return {"error": "S", "mensaje": "No tiene horarios asignados"}

    lugar = await lugar_asignado(data['employee_id'])

    if len(lugar) == 0:
        return {"error": "S", "mensaje": "No tiene un lugar de trabajo asignado"}

    sql = f"INSERT INTO rol.tasistencias (usuario_codigo, entrada, horarios, lugar_asignado, jornada) VALUES ({data['employee_id']}, NOW(), '{json.dumps(horarios)}', {lugar[0]['coordenadas_codigo']}, {data['jornada']}) RETURNING codigo"

    return query_handler.execute_sql(sql, "Registro de entrada exitoso")


@router.put("/registrar_salida")
async def registrar_salida(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    horarios = await horarios_asignados(data['employee_id'])

    if len(horarios) == 0:
        return {"error": "S", "mensaje": "No tiene horarios asignados"}

    lugar = await lugar_asignado(data['employee_id'])

    if len(lugar) == 0:
        return {"error": "S", "mensaje": "No tiene un lugar de trabajo asignado"}

    sql = f"UPDATE rol.tasistencias SET salida = NOW() WHERE codigo = (SELECT codigo FROM rol.tasistencias WHERE usuario_codigo = {data['employee_id']} ORDER BY entrada DESC LIMIT 1) AND salida IS NULL RETURNING codigo"

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
                    "mensaje": "No se encontraron registros",
                    "objetos": rows,
                }
            asistencias = [row._asdict() for row in rows]
            excepciones = await excepciones_autorizadas(usuario_codigo)
            nuevas_asistencias = utils.nuevas_asistencias(asistencias, excepciones)
            
            return {"error": "N", "mensaje": "", "objetos": nuevas_asistencias}

    except Exception as error:
        return {"error": "S", "mensaje": str(error)}
    offset = (int(numero_de_pagina) - 1) * int(registros_por_pagina)

    # Diccionario para mapear nombres de meses a números
    meses = {
        'Enero': 1,
        'Febrero': 2,
        'Marzo': 3,
        'Abril': 4,
        'Mayo': 5,
        'Junio': 6,
        'Julio': 7,
        'Agosto': 8,
        'Septiembre': 9,
        'Octubre': 10,
        'Noviembre': 11,
        'Diciembre': 12
    }

    # Obtener el número del mes a partir del texto recibido
    mes_numero = meses.get(mes)

    # Obtener fecha inicial
    fecha_desde = datetime(int(anio), mes_numero, 1)

    # Obtener fecha final sumando un mes y restando un segundo
    fecha_hasta = fecha_desde + timedelta(days=32)
    fecha_hasta = datetime(fecha_hasta.year, fecha_hasta.month, 1) - timedelta(seconds=1)

    # Formatear las fechas en el formato adecuado
    fecha_desde_str = fecha_desde.strftime('%Y/%m/%d')
    fecha_hasta_str = fecha_hasta.strftime('%Y/%m/%d %H:%M:%S')

    query = f"SELECT tasistencias.codigo, templeado.nombres || ' ' || templeado.apellidos AS nombre_completo, talmacen.alm_nomcom as lugar_asignado, entrada, salida FROM rol.tasistencias INNER JOIN rol.templeado ON tasistencias.usuario_codigo = templeado.codigo INNER JOIN rol.tlugaresasignados ON tasistencias.usuario_codigo = tlugaresasignados.usuario_codigo INNER JOIN rol.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN comun.talmacen ON talmacen.alm_codigo = tcoordenadas.alm_codigo WHERE tasistencias.usuario_codigo = {usuario_codigo} AND entrada BETWEEN '{fecha_desde_str}' AND '{fecha_hasta_str}' ORDER BY entrada OFFSET {offset} ROWS FETCH FIRST {registros_por_pagina} ROWS ONLY"

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
                    "mensaje": "No se encontraron registros",
                    "objetos": rows,
                }
            asistencias = [row._asdict() for row in rows]

            excepciones = await excepciones_autorizadas(usuario_codigo)
            
            nuevas_asistencias = utils.nuevas_asistencias(asistencias, excepciones)

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


async def empleados_asistencias(desde: str, hasta: str):
    # sql = "SELECT usuario_codigo FROM rol.tasistencias ORDER BY usuario_codigo"
    sql = f"SELECT usuario_codigo FROM rol.tasistencias WHERE entrada BETWEEN '{desde}' AND '{hasta}' ORDER BY usuario_codigo"
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


from datetime import datetime, timedelta

def calcular_jornadas(resultados, fecha, nuevas_asistencias, entrada, salida, jornada):
    horas_trabajadas = 0
    atrasos = 0

    for horario in resultados:
        if horario[0] == str(fecha):
            jornadas = horario[1:]  # Obtenemos las jornadas del día
            hora_inicio1, hora_fin1 = jornadas[0].split()
            inicio1 = datetime.strptime(hora_inicio1, '%H:%M').time()
            fin1 = datetime.strptime(hora_fin1, '%H:%M').time()

            if len(jornadas) > 1 and jornadas[1]:
                hora_inicio2, hora_fin2 = jornadas[1].split()
                inicio2 = datetime.strptime(hora_inicio2, '%H:%M').time()
                fin2 = datetime.strptime(hora_fin2, '%H:%M').time()
            else:
                inicio2, fin2 = None, None

            horas_jornadas = 0
            # Calcular horas por jornada
            horas_jornada1 = (datetime.combine(fecha, fin1) - datetime.combine(fecha, inicio1)).seconds / 3600
            horas_jornadas += horas_jornada1
            
            if inicio2 and fin2:
                horas_jornada2 = (datetime.combine(fecha, fin2) - datetime.combine(fecha, inicio2)).seconds / 3600
                horas_jornadas += horas_jornada2
            
            if len(nuevas_asistencias) == 1 and jornadas[1] != '':
                if jornada == 1 and salida and inicio2:
                    if salida > datetime.combine(fecha, inicio2):
                        horas_totales_jornadas = horas_jornada1 + horas_jornada2
                        
                        horas_primera = utils.calcular_horas(fecha, 1, inicio1, fin1, None, None, entrada, min(salida, datetime.combine(fecha, fin1)))
                        
                        horas_segunda = utils.calcular_horas(fecha, 2, None, None, inicio2, fin2, datetime.combine(fecha, inicio2), min(salida, datetime.combine(fecha, fin2)))

                        horas_realmente_trabajadas = horas_primera + horas_segunda
                        
                        horas_trabajadas = min(horas_realmente_trabajadas, horas_totales_jornadas)
                        atrasos += utils.calcular_atrasos(1, inicio1, fin1, None, None, entrada, salida)
                    else:
                        horas_trabajadas = utils.calcular_horas(fecha, 1, inicio1, fin1, None, None, entrada, min(salida, datetime.combine(fecha, fin1)))
                        atrasos = utils.calcular_atrasos(1, inicio1, fin1, None, None, entrada, salida)    

                if jornada == 2 and salida:
                    horas_trabajadas = utils.calcular_horas(fecha, 2, None, None, inicio2, fin2, entrada, salida)
                    atrasos = utils.calcular_atrasos(2, None, None, inicio2, fin2, entrada, min(salida, datetime.combine(fecha, fin2)))
                    if horas_trabajadas >= horas_jornadas:
                        horas_trabajadas = max(0, horas_jornadas - (atrasos / 60))

            else:
                if jornada == 1:    
                    # Si la salida es al día siguiente
                    if salida.date() > entrada.date():
                        fin1_ajustado = datetime.combine(fecha + timedelta(days=1), fin1)
                    else:
                        fin1_ajustado = datetime.combine(fecha, fin1)
                    horas_trabajadas += utils.calcular_horas(fecha, jornada, inicio1, fin1, None, None, entrada, min(salida, fin1_ajustado))
                    atrasos += utils.calcular_atrasos(jornada, inicio1, fin1, None, None, entrada, salida)

                elif jornada == 2:
                    horas_trabajadas += utils.calcular_horas(fecha, jornada, None, None, inicio2, fin2, entrada, min(salida, datetime.combine(fecha, fin2)))
                    atrasos += utils.calcular_atrasos(jornada, None, None, inicio2, fin2, entrada, salida)

                if horas_trabajadas >= horas_jornadas:
                    horas_trabajadas = horas_jornadas

    return horas_trabajadas, atrasos



async def calcular(usuario_codigo: int, fecha_desde: str, fecha_hasta: str):
    fecha_hasta = datetime.strptime(unquote(fecha_hasta), '%Y/%m/%d')
    fecha_hasta = fecha_hasta + timedelta(days=1) - timedelta(seconds=1)
    query = f"SELECT entrada, salida, jornada FROM rol.tasistencias WHERE usuario_codigo = {usuario_codigo} AND entrada BETWEEN '{unquote(fecha_desde)}' AND '{fecha_hasta}'"
    excepciones = await excepciones_autorizadas(usuario_codigo)
    fechas = utils.obtener_fechas(fecha_desde, fecha_hasta)

    with Session(engine) as session:
        rows = session.execute(text(query)).fetchall()
        if len(rows) == 0:
            return {
                "error": "S",
                "mensaje": "",
                "objetos": rows,
            }

        asistencias = [row._asdict() for row in rows]
        nuevas_asistencias = utils.nuevas_asistencias(asistencias, excepciones)
    
        horarios = []
            
        for fecha in fechas:
            info = await get_horario_info(usuario_codigo, fecha[0], fecha[1])
            if len(info) > 0:
                horarios.append(info[0]['horario'])
        
        resultados = utils.get_horarios(horarios)
        
        horas_trabajadas = 0
        atrasos = 0
        
        for asistencia in nuevas_asistencias:
            entrada = asistencia["entrada"]
            salida = asistencia["salida"]
            jornada = asistencia["jornada"]
            
            fecha = entrada.date()
            inicio1, inicio2 = '', ''
            fin1, fin2 = '', ''
            
            # Filtrar asistencias por la fecha actual
            asistencias_dia = [a for a in nuevas_asistencias if a["entrada"].date() == fecha]
            
            # Usamos la función para calcular horas trabajadas y atrasos solo para las asistencias del día
            horas_asistencia, atrasos_asistencia = calcular_jornadas(resultados, fecha, asistencias_dia, entrada, salida, jornada)
            
            # Sumamos los resultados a las horas y atrasos totales
            horas_trabajadas += horas_asistencia
            atrasos += atrasos_asistencia
                        
    return {
        "horas_trabajadas": round(horas_trabajadas, 2),
        "atrasos": round(atrasos, 2),
    }


async def get_horarios(codigo: int):
    sql = f"SELECT DISTINCT horarios FROM rol.tasistencias WHERE usuario_codigo = {codigo}"
    with Session(engine) as session:
        rows = session.execute(text(sql)).fetchall()
        objetos = [row._asdict() for row in rows]

        horarios = []
        for objeto in objetos:
            horarios_objeto = [horario['codigo'] for horario in objeto['horarios']]
            horarios.extend(horarios_objeto)  
        
        return horarios
    
    
async def get_horarios_asignados(codigo: int, mes: int, anio: int):    
    sql = f"SELECT horarios FROM rol.tasistencias WHERE usuario_codigo = {codigo}"


@router.get('/verificar_horarios_asignados')
async def verificar_horarios_asignados(request: Request, codigo: int, horario: int, nombre: str):
    token = request.headers.get('token')
    sql = f"SELECT DISTINCT (jsonb_array_elements(horarios::jsonb) ->> 'codigo')::int AS codigo FROM rol.tasistencias WHERE usuario_codigo = {codigo}"
    horario_asignado = False
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
            valores = [d['codigo'] for d in codigos]  

            if (horario in valores):
                horario_asignado = True

            return {"error": "N", "mensaje": nombre, "objetos": horario_asignado}

    except Exception as e:
        return {"error": "S", "mensaje": str(e), "objetos": horario_asignado}


async def get_horario_info(codigo: int, mes: int, anio: int):    
    sql = f"SELECT horario FROM rol.thorariosasignados WHERE usuario_codigo = {codigo} AND mes = {mes} AND anio = {anio}"
    with Session(engine) as session:
        rows = session.execute(text(sql)).fetchall()
        objetos = [row._asdict() for row in rows]
        return objetos


@router.get("/calcular_horas_atrasos")
async def calcular_horas_atrasos(request: Request, lugar: str, fecha_desde: str, fecha_hasta: str):
    token = request.headers.get('token')

    try:
        token_middleware.verify_token(token)
        with Session(engine) as session:
            employees = await empleados_asignados(lugar)
            codigos = await empleados_asistencias(fecha_desde, fecha_hasta)

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


@router.get("/obtener_atrasos")
async def obtener_atrasos(request: Request, usuario_codigo, fecha_desde, fecha_hasta):
    fecha_hasta = datetime.strptime(fecha_hasta, '%Y/%m/%d')
    fecha_hasta = fecha_hasta + timedelta(days=1) - timedelta(seconds=1)
    
    fechas = utils.obtener_fechas(fecha_desde, fecha_hasta)

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
        
    try:
        with Session(engine) as session:
            rows = session.execute(text(query)).fetchall()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": "No se encontraron registros",
                    "objetos": rows,
                }

            asistencias = [row._asdict() for row in rows]
            excepciones = await excepciones_autorizadas(usuario_codigo)
            nuevas_asistencias = utils.nuevas_asistencias(asistencias, excepciones)

            horarios = []
            
            for fecha in fechas:
                info = await get_horario_info(usuario_codigo, fecha[0], fecha[1])
                if len(info) > 0:
                    horarios.append(info[0]['horario'])
                    
            resultados = utils.get_horarios(horarios)    
            
            atrasos = []      
            
            for asistencia in nuevas_asistencias:
                entrada = asistencia["entrada"]
                salida = asistencia["salida"]

                fecha = entrada.date()
                hora_entrada = entrada.time()  
                hora_salida = salida.time()

                # Buscar el horario correspondiente a la fecha de la asistencia
                for horario in resultados:
                    if horario[0]  == str(fecha):
                        jornadas = horario[1:]  # Obtenemos las jornadas del día
                        # Iterar sobre las jornadas para verificar si hay retrasos
                        for jornada in jornadas:
                            if jornada:  # Verificar si la jornada no está vacía
                                hora_inicio, hora_fin = jornada.split()  
                                
                                atraso1 = utils.datetime_to_seconds(hora_entrada) - utils.time_to_seconds(hora_inicio)
                                
                                atraso2 = utils.time_to_seconds(hora_fin) - utils.datetime_to_seconds(hora_salida)
                                
                                if atraso1 > 300 and atraso1 < 10800:
                                    atrasos.append(asistencia)
                                    
                                if atraso2 > 300 and atraso2 < 10800:
                                    atrasos.append(asistencia)    
            return {"error": "N", "mensaje": "", "objetos": atrasos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}     