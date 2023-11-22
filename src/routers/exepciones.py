import json
import fastapi
from src import config
from fastapi import Request
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
async def obtener_empleados_lugares(request: Request):
    sql = f"SELECT templeado.codigo as usuario_codigo, templeado.nombres || ' ' || templeado.apellidos AS nombre_completo, talmacen.alm_nomcom FROM comun.tlugaresasignados INNER JOIN comun.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN comun.talmacen ON talmacen.alm_codigo = tcoordenadas.alm_codigo INNER JOIN rol.templeado ON tlugaresasignados.usuario_codigo = templeado.codigo ORDER BY nombre_completo"
    token = request.headers.get('token')

    return query_handler.execute_sql_token(sql, token, "")


@router.post("/registrar_exepcion")
async def registrar_exepcion(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    usuario_codigo = data['usuario_codigo']
    excepcion = data['excepcion']
    dias = data['dias']
    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 829, 1)

    if acceso[0]['tiene_acceso'] != '':
        return {
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }

    sql = f"INSERT INTO comun.texcepciones (usuario_codigo, excepcion, dias) VALUES ('{usuario_codigo}', '{excepcion.strip()}', ARRAY{dias}) RETURNING id"

    return query_handler.execute_sql_token(sql, token, "Registro de excepción exitoso")


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
    sql = f"UPDATE comun.texcepciones SET autorizado_por = '{autorizado_por}', autorizado = true WHERE id = '{usuario_codigo}' RETURNING id"

    return query_handler.execute_sql_token(sql, token, "Excepción autorizada con exitoso")


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
    sql = f"UPDATE comun.texcepciones SET autorizado_por = NULL, autorizado = false WHERE id = {id} RETURNING id"

    return query_handler.execute_sql_token(sql, token, "La autorización se ha eliminado con éxito.")


@router.get("/obtener_excepciones")
async def obtener_excepciones(request: Request):
    token = request.headers.get('token')
    sql = "SELECT texcepciones.id as usuario_codigo, templeado.nombres || ' ' || templeado.apellidos AS nombre_completo, talmacen.alm_nomcom, texcepciones.excepcion, texcepciones.dias FROM comun.tlugaresasignados INNER JOIN comun.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN comun.talmacen ON talmacen.alm_codigo = tcoordenadas.alm_codigo INNER JOIN rol.templeado ON tlugaresasignados.usuario_codigo = templeado.codigo INNER JOIN comun.texcepciones ON texcepciones.usuario_codigo = templeado.codigo WHERE texcepciones.autorizado = false ORDER BY nombre_completo"

    return query_handler.execute_sql_token(sql, token, "")


@router.get("/obtener_excepciones_autorizadas")
async def obtener_excepciones_autorizadas(request: Request, desde: str = None, hasta: str = None):
    token = request.headers.get('token')
    sql = "SELECT texcepciones.id, templeado.nombres || ' ' || templeado.apellidos AS nombre_completo, texcepciones.excepcion, texcepciones.dias, TUsuario.usu_nomape AS autorizado_por FROM comun.texcepciones INNER JOIN rol.templeado AS templeado ON texcepciones.usuario_codigo = templeado.codigo INNER JOIN usuario.TUsuario ON texcepciones.autorizado_por = TUsuario.usu_codigo WHERE texcepciones.autorizado = TRUE"

    return query_handler.get_exceptions(sql, token, desde, hasta)
