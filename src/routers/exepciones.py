import json
import fastapi
from typing import List
from fastapi import Request
from src.config import config
from sqlalchemy import create_engine
from src.middleware import acceso_middleware
from src.routers.controllers import SessionHandler

# Establish connections to PostgreSQL databases for "apromed"
engine = create_engine(config.db_uri2)

# API Route Definitions
router = fastapi.APIRouter()

# Crear una instancia de la clase con tu motor de base de datos
query_handler = SessionHandler(engine)


@router.get("/obtener_empleados_lugares")
async def obtener_empleados_lugares(request: Request, departamento: str = None):
    sql = "SELECT templeado.codigo as usuario_codigo, templeado.nombres || ' ' || templeado.apellidos AS nombre_completo, TPlantillaRol.descripcion AS departamento, talmacen.alm_nomcom FROM rol.tlugaresasignados INNER JOIN rol.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN comun.talmacen ON talmacen.alm_codigo = tcoordenadas.alm_codigo INNER JOIN rol.templeado ON tlugaresasignados.usuario_codigo = templeado.codigo INNER JOIN rol.TPlantillaRol ON TEmpleado.codigo_plantilla = TPlantillaRol.codigo"
    token = request.headers.get('token')
    if departamento not in [None, '', 'N']:
        sql += f" WHERE TPlantillaRol.descripcion LIKE '{departamento}'"

    sql += " ORDER BY nombre_completo"
    
    return query_handler.execute_sql_token(sql, token, "")

@router.get("/buscar_excepciones")
async def buscar_excepciones(request: Request, usuario_codigo: int, dia: str):
    sql = f"""
        SELECT nombre_completo, array_agg(DISTINCT fecha) AS fechas_conflictivas
        FROM (
            SELECT unnest(dias) AS fecha, templeado.nombres || ' ' || templeado.apellidos AS nombre_completo
            FROM rol.texcepciones
            INNER JOIN rol.templeado ON texcepciones.usuario_codigo = templeado.codigo 
            WHERE texcepciones.usuario_codigo = {usuario_codigo} AND texcepciones.excepcion != ''
        ) sub
        WHERE fecha = '{dia}'
        GROUP BY nombre_completo;
    """
    token = request.headers.get('token')
    return query_handler.execute_sql_token(sql, token, "")


@router.post("/registrar_exepcion")
async def registrar_exepcion(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 829, 1)

    if acceso[0]['tiene_acceso'] != '':
        return {
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }

    sql = f"INSERT INTO rol.texcepciones (usuario_codigo, excepcion, dias) VALUES ('{data['usuario_codigo']}', '{data['excepcion'].strip()}', ARRAY{data['dias']}) RETURNING id"

    return query_handler.execute_sql_token(sql, token, "Registro de excepción exitoso")


@router.get("/obtener_vacaciones")
async def obtener_vacaciones(request: Request, usuario_codigo: str = None):
    sql = f"SELECT texcepciones.id AS codigo, dias FROM rol.texcepciones WHERE excepcion = 'Vacaciones' AND usuario_codigo = {usuario_codigo}"
    
    token = request.headers.get('token')

    return query_handler.execute_sql_token(sql, token, "")
    

@router.put("/autorizar_exepcion")
async def autorizar_exepcion(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    usuario_codigo = data['usuario_codigo']
    autorizado_por = data['autorizado_por']
    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 829, 2)
    if acceso[0]['tiene_acceso'] != '':
        return {
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }
    sql = f"UPDATE rol.texcepciones SET autorizado_por = {autorizado_por}, autorizado = true WHERE id = '{usuario_codigo}' RETURNING id"

    return query_handler.execute_sql_token(sql, token, "Excepción autorizada con exitoso")


@router.delete("/eliminar_exepcion")
async def eliminar_exepcion(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    id = data['id']
    # excepcion = data['excepcion']
    # dias = data['dias']
    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 829, 1)

    if acceso[0]['tiene_acceso'] != '':
        return {
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }

    sql = f"DELETE FROM rol.texcepciones where id = {id} RETURNING id"

    return query_handler.execute_sql_token(sql, token, "Exepción eliminada exitosamente")


@router.put("/desautorizar_exepcion")
async def desautorizar_exepcion(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    id = data['id']
    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 829, 3)

    if acceso[0]['tiene_acceso'] != '':
        return {
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }
    sql = f"UPDATE rol.texcepciones SET autorizado_por = NULL, autorizado = false WHERE id = {id} RETURNING id"

    return query_handler.execute_sql_token(sql, token, "La autorización se ha eliminado con éxito.")


@router.get("/obtener_excepciones_usuario")
async def obtener_excepciones_usuario(request: Request, usuario_codigo: int, autorizado: bool):
    sql = f"""
        WITH anio AS (
            SELECT
                id,
                excepcion,
                ARRAY(
                    SELECT to_date(fecha, 'YYYY/MM/DD')
                    FROM unnest(dias) AS fecha
                    WHERE date_part('year', to_date(fecha, 'YYYY/MM/DD')) = date_part('year', current_date)
                ) AS fechas_filtradas
            FROM rol.texcepciones
            WHERE usuario_codigo = {usuario_codigo} AND excepcion != '' AND autorizado = {autorizado}
        )
        SELECT id, excepcion, fechas_filtradas AS dias
        FROM anio
        WHERE array_length(fechas_filtradas, 1) > 0
        ORDER BY id;
        """

    return query_handler.execute_sql(sql, "")


@router.get("/obtener_excepciones")
async def obtener_excepciones(request: Request, departamento: str = None):
    sql = "SELECT texcepciones.id as codigo, texcepciones.usuario_codigo, templeado.nombres || ' ' || templeado.apellidos AS nombre_completo, TPlantillaRol.descripcion AS departamento, talmacen.alm_nomcom, texcepciones.excepcion, texcepciones.dias FROM rol.tlugaresasignados INNER JOIN rol.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN comun.talmacen ON talmacen.alm_codigo = tcoordenadas.alm_codigo INNER JOIN rol.templeado ON tlugaresasignados.usuario_codigo = templeado.codigo INNER JOIN rol.texcepciones ON texcepciones.usuario_codigo = templeado.codigo INNER JOIN rol.TPlantillaRol ON TEmpleado.codigo_plantilla = TPlantillaRol.codigo WHERE texcepciones.autorizado = false AND texcepciones.excepcion != ''"
    token = request.headers.get('token')
    
    if departamento not in [None, '', 'N']:
        sql += f" AND TPlantillaRol.descripcion LIKE '{departamento}'"

    sql += " ORDER BY nombre_completo"

    return query_handler.execute_sql_token(sql, token, "")

@router.get("/obtener_numero_autorizadas")
async def obtener_numero_autorizadas(request: Request, desde: str = None, hasta: str = None):
    token = request.headers.get('token')
    sql = """
        SELECT COUNT(*) AS total
        FROM 
            rol.texcepciones 
        INNER JOIN 
            rol.templeado AS templeado ON texcepciones.usuario_codigo = templeado.codigo 
        INNER JOIN 
            usuario.TUsuario ON texcepciones.autorizado_por = TUsuario.usu_codigo 
        INNER JOIN 
            rol.TPlantillaRol ON TEmpleado.codigo_plantilla = TPlantillaRol.codigo 
        WHERE 
            texcepciones.autorizado = TRUE 
            AND texcepciones.excepcion != ''
    """
    if desde and hasta:
        sql += f"""
            AND EXISTS (
                SELECT 1 
                FROM unnest(texcepciones.dias) AS fecha 
                WHERE fecha::date BETWEEN '{desde}' AND '{hasta}'
            )
        """
    return query_handler.execute_sql_token(sql, token, "")    

@router.get("/obtener_excepciones_autorizadas")
async def obtener_excepciones_autorizadas(request: Request, desde: str = None, hasta: str = None, numeroDePagina: int = 0, registrosPorPagina: int= 0):
    offset = (numeroDePagina - 1) * registrosPorPagina
    token = request.headers.get('token')
    sql = f"""
        SELECT 
            texcepciones.id as codigo, 
            texcepciones.usuario_codigo, 
            templeado.nombres || ' ' || templeado.apellidos AS nombre_completo, 
            TPlantillaRol.descripcion AS departamento, 
            texcepciones.excepcion, 
            texcepciones.dias, 
            TUsuario.usu_nomape AS autorizado_por 
        FROM 
            rol.texcepciones 
        INNER JOIN 
            rol.templeado AS templeado ON texcepciones.usuario_codigo = templeado.codigo 
        INNER JOIN 
            usuario.TUsuario ON texcepciones.autorizado_por = TUsuario.usu_codigo 
        INNER JOIN 
            rol.TPlantillaRol ON TEmpleado.codigo_plantilla = TPlantillaRol.codigo 
        WHERE 
            texcepciones.autorizado = TRUE 
            AND texcepciones.excepcion != ''
    """
    
    if desde and hasta:
        sql += f"""
            AND EXISTS (
                SELECT 1 
                FROM unnest(texcepciones.dias) AS fecha 
                WHERE fecha::date BETWEEN '{desde}' AND '{hasta}'
            )
        """
    
    sql += f" ORDER BY codigo DESC OFFSET {offset} ROWS FETCH FIRST {registrosPorPagina} ROWS ONLY"   
    return query_handler.execute_sql_token(sql, token, "")

@router.get("/obtener_dias_permisos")
async def obtener_permisos(request: Request, id: int = None):
    sql = f"SELECT dias FROM rol.texcepciones WHERE id = {id}"
    token = request.headers.get('token')
    return query_handler.execute_sql_token(sql, token, "")

@router.put("/actualizar_permiso")
async def actualizar_permiso(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    token = request.headers.get('token')
    
    dias_value = '{}'
    
    auditoria_text = f"Cargo a vacaciones hecho por: {data['usuario']}\nusuario: {data['empleado']}\npermiso: {data['permiso']} => vacacion: {data['dia']}"
    
    sql = f"""
    UPDATE rol.texcepciones
    SET excepcion = '', 
        dias = '{dias_value}',
        auditoria = CASE 
                        WHEN auditoria IS NULL THEN ''
                        ELSE auditoria || '\n-------\n'
                    END || '{auditoria_text}'
    WHERE id = {data['id']} RETURNING id;
    """
    
    return query_handler.execute_sql_token(sql, token, "Permiso actualizado con éxito.")  

@router.put("/actualizar_dias_permisos")
async def actualizar_dias_permisos(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    token = request.headers.get('token')
    
    auditoria_text = f"Cargo a vacaciones hecho por: {data['usuario']}\nusuario: {data['empleado']}\npermiso: {data['permiso']} => vacacion: {data['dia']}"
    
    sql = f"""
    UPDATE rol.texcepciones
    SET dias = array_remove(dias, '{data['permiso']}'), 
        auditoria = CASE 
                        WHEN auditoria IS NULL THEN ''
                        ELSE auditoria || '\n-------\n'
                    END || '{auditoria_text}'
    WHERE id = {data['id']} RETURNING id;
    """
    
    return query_handler.execute_sql_token(sql, token, "Día de permiso actualizado con éxito.") 

@router.get("/obtener_dias_vacaciones")
async def obtener_dias_vacaciones(request: Request, fecha: str, usuario: int = None):
    token = request.headers.get('token')
    
    sql = f"SELECT id as codigo, (cardinality(dias) = 1) AS is_single_date FROM rol.texcepciones WHERE '{fecha}' = ANY(dias) AND usuario_codigo = {usuario} AND excepcion = 'Vacaciones';"
    
    return query_handler.execute_sql_token(sql, token, "")

@router.put("/actualizar_dias_vacaciones")
async def actualizar_dias_vacaciones(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    token = request.headers.get('token')
    
    sql = f"""
    UPDATE rol.texcepciones
    SET dias = array_remove(dias, '{data['vacacion']}')
    WHERE id = {data['id']} RETURNING id;
    """
    
    return query_handler.execute_sql_token(sql, token, "Día de vacación eliminado con éxito.") 
    
@router.delete("/eliminar_dia_vacacion")
async def eliminar_dia_vacacion(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    token = request.headers.get('token')
    
    sql = f"""
    DELETE FROM rol.texcepciones
    WHERE id = {data['id']} RETURNING id;
    """
    
    return query_handler.execute_sql_token(sql, token, "Día de vacación eliminado con éxito.") 


@router.put("/actualizar_excepciones")   
async def actualizar_excepciones(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    token = request.headers.get('token')
    sql = f"""
    UPDATE rol.texcepciones
    SET dias = ARRAY{data['dias']}
    WHERE id = {data['id']} RETURNING id;
    """
    
    return query_handler.execute_sql_token(sql, token, "Días de excepción actualizados con éxito.")