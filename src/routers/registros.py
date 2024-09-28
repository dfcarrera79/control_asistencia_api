import json
import fastapi
from src.config import config
from fastapi import Request
from sqlalchemy import create_engine
from src.middleware import acceso_middleware
from src.routers.controllers import SessionHandler

# Establish connections to PostgreSQL databases for "apromed"
engine = create_engine(config.db_uri)

# API Route Definitions
router = fastapi.APIRouter()

# Crear una instancia de la clase con tu motor de base de datos
query_handler = SessionHandler(engine)


@router.get("/obtener_dispositivos")
async def obtener_dispositivos(request: Request, departamento: str):
    sql = f"SELECT tdispositivo.codigo, TEmpleado.cedula_ruc, TEmpleado.nombres || ' ' || TEmpleado.apellidos AS nombre_completo, TPlantillaRol.descripcion AS departamento, tdispositivo.id_dispositivo, tdispositivo.es_master FROM rol.TEmpleado INNER JOIN rol.TPlantillaRol ON TEmpleado.codigo_plantilla = TPlantillaRol.codigo INNER JOIN rol.tdispositivo ON TEmpleado.codigo = tdispositivo.usuario_codigo WHERE TEmpleado.desafectado = 'N'"
    token = request.headers.get('token')

    if departamento not in [None, '', 'N']:
        sql += f" AND TPlantillaRol.descripcion LIKE '{departamento}'"

    sql += " ORDER BY nombre_completo"

    return query_handler.execute_sql_token(sql, token, "")


@router.get("/obtener_fotos")
async def obtener_fotos(request: Request, departamento: str):
    sql = f"SELECT tfoto.id_foto, TEmpleado.cedula_ruc, TEmpleado.nombres || ' ' || TEmpleado.apellidos AS nombre_completo, TPlantillaRol.descripcion AS departamento, tfoto.path FROM rol.TEmpleado INNER JOIN rol.TPlantillaRol ON TEmpleado.codigo_plantilla = TPlantillaRol.codigo INNER JOIN rol.tfoto ON TEmpleado.codigo = tfoto.usuario_codigo WHERE TEmpleado.desafectado = 'N'"
    token = request.headers.get('token')

    if departamento not in [None, '', 'N']:
        sql += f" AND TPlantillaRol.descripcion LIKE '{departamento}'"

    sql += " ORDER BY nombre_completo"

    return query_handler.execute_sql_token(sql, token, "")


@router.delete('/eliminar_foto')
async def eliminar_foto(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    id_foto = data['id_foto']
    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 824, 3)

    if acceso[0]['tiene_acceso'] != '':
        return {
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }

    sql = f"DELETE FROM rol.tfoto WHERE id_foto = {id_foto} RETURNING path, usuario_codigo"

    return query_handler.execute_sql_token(sql, token, "Registro eliminado exitosamente")


@router.delete('/eliminar_cel')
async def eliminar_cel(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    codigo = data['codigo']
    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 823, 3)

    if acceso[0]['tiene_acceso'] != '':
        return {
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }

    sql = f"DELETE FROM rol.tdispositivo WHERE codigo = {codigo} RETURNING id_dispositivo, usuario_codigo"

    return query_handler.execute_sql_token(sql, token, "Registro eliminado exitosamente")


@router.post("/copiar_path_id")
async def copiar_path_id(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    usuario_codigo = data['usuario_codigo']
    pathorid = data['pathorid']
    anulado_por = data['anulado_por']
    token = request.headers.get('token')
    sql = f"INSERT INTO rol.trespaldofotocel (usuario_codigo, pathorid, anulado_por, fecha) VALUES({usuario_codigo}, '{pathorid}', {anulado_por}, NOW()) RETURNING id_registro"
    return query_handler.execute_sql_token(sql, token, "Registro anulado exitosamente")


@router.post("/master_path_id")
async def master_path_id(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    token = request.headers.get('token')
    sql = f"INSERT INTO rol.trespaldofotocel (usuario_codigo, pathorid, master_por, fecha) VALUES({data['usuario_codigo']}, '{data['pathorid']}', {data['master_por']}, NOW()) RETURNING id_registro"
    return query_handler.execute_sql_token(sql, token, "Registro de dispositivo master exitoso")


@router.get("/obtener_numero_registros")
async def obtener_numero_registros(request: Request, departamento: str):
    sql = "SELECT COUNT(*) AS total FROM rol.trespaldofotocel INNER JOIN rol.TEmpleado ON trespaldofotocel.usuario_codigo = TEmpleado.codigo LEFT JOIN usuario.TUsuario AnuladoPor ON trespaldofotocel.anulado_por = AnuladoPor.usu_codigo LEFT JOIN usuario.TUsuario MasterPor ON trespaldofotocel.master_por = MasterPor.usu_codigo INNER JOIN rol.TPlantillaRol ON TEmpleado.codigo_plantilla = TPlantillaRol.codigo"
    
    if departamento not in [None, '', 'N']:
        sql += f" AND TPlantillaRol.descripcion LIKE '{departamento}'"
    
    token = request.headers.get('token')
    return query_handler.execute_sql_token(sql, token, "")

@router.get("/obtener_anulados")
async def obtener_anulados(request: Request, departamento: str, numeroDePagina: int, registrosPorPagina: int):
    
    offset = (numeroDePagina - 1) * registrosPorPagina
    
    sql = "SELECT id_registro AS codigo, TEmpleado.nombres || ' ' || TEmpleado.apellidos AS nombre_completo, TPlantillaRol.descripcion AS departamento, pathorid AS registro, AnuladoPor.usu_nomape AS anulado_por, MasterPor.usu_nomape AS master_por, fecha FROM rol.trespaldofotocel INNER JOIN rol.TEmpleado ON trespaldofotocel.usuario_codigo = TEmpleado.codigo LEFT JOIN usuario.TUsuario AnuladoPor ON trespaldofotocel.anulado_por = AnuladoPor.usu_codigo LEFT JOIN usuario.TUsuario MasterPor ON trespaldofotocel.master_por = MasterPor.usu_codigo INNER JOIN rol.TPlantillaRol ON TEmpleado.codigo_plantilla = TPlantillaRol.codigo"
    token = request.headers.get('token')

    if departamento not in [None, '', 'N']:
        sql += f" AND TPlantillaRol.descripcion LIKE '{departamento}'"
    
    sql += f" ORDER BY nombre_completo DESC OFFSET {offset} ROWS FETCH FIRST {registrosPorPagina} ROWS ONLY"

    return query_handler.execute_sql_token(sql, token, "")


@router.put("/asignar_master")    
async def asignar_master(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    token = request.headers.get('token')
    sql = f"UPDATE rol.tdispositivo SET es_master = TRUE WHERE codigo = '{data['codigo']}' RETURNING id_dispositivo, usuario_codigo"
    return query_handler.execute_sql_token(sql, token, "Asignación de dispositivo master exitosa")


@router.put("/remover_master")    
async def remover_master(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    token = request.headers.get('token')
    sql = f"UPDATE rol.tdispositivo SET es_master = FALSE WHERE codigo = '{data['codigo']}' RETURNING codigo"
    return query_handler.execute_sql_token(sql, token, "El dispositivo ha sido removido como master exitosamente")
