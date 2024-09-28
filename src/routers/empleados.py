import json
import fastapi
from fastapi import Request
from src.utils import utils
from src.config import config
from sqlalchemy import create_engine
from src.middleware import acceso_middleware
from src.routers.controllers import SessionHandler

# Establish connections to PostgreSQL databases for "apromed"
engine = create_engine(config.db_uri)

# API Route Definitions
router = fastapi.APIRouter()

# Crear una instancia de la clase con tu motor de base de datos
query_handler = SessionHandler(engine)


@router.get("/obtener_empleado")
async def obtener_empleado(request: Request, departamento: str):
    sql = f"SELECT TEmpleado.codigo, TEmpleado.cedula_ruc, TEmpleado.nombres || ' ' || TEmpleado.apellidos AS nombre_completo, TEmpleado.direccion, TEmpleado.cargo, TEmpleado.sueldo_basico, TEmpleado.fecha_ingreso, TEmpleado.no_telefono, TEmpleado.no_celular, TEmpleado.email, TPlantillaRol.descripcion AS departamento, CASE WHEN sexo = 'M' THEN 'Masculino' ELSE 'Femenino' END AS genero, CASE WHEN estado_civil = 'S' THEN 'Soltero(a)' WHEN estado_civil = 'C' THEN 'Casado(a)' WHEN estado_civil = 'D' THEN 'Divorciado(a)' WHEN estado_civil = 'V' THEN 'Viudo(s)' ELSE 'Unión Libre' END AS civil FROM rol.TEmpleado INNER JOIN rol.TPlantillaRol ON TEmpleado.codigo_plantilla = TPlantillaRol.codigo AND desafectado LIKE 'N'"

    token = request.headers.get('token')

    if departamento not in [None, '', 'N']:
        sql += f"WHERE TPlantillaRol.descripcion LIKE '{departamento}'"

    sql += " ORDER BY apellidos"

    return query_handler.execute_sql_token(sql, token, "")

@router.get("/obtener_horario_empleado")
async def obtener_horario_empleado(codigo: int, mes: int, anio: int):
    sql = f"SELECT horario FROM rol.thorariosasignados WHERE usuario_codigo = {codigo}"
    
    if mes not in [None, '', 'N', '0', 0]:
        sql += f" AND mes = {mes}"

    if anio not in [None, '', 'N', '0', 0]:
        sql += f" AND anio = {anio}"
    
    return query_handler.execute_sql(sql, "")    


@router.get("/obtener_empleado_suplementarias")
async def obtener_empleado(request: Request, departamento: str):
    sql = f"SELECT TEmpleado.codigo, TEmpleado.nombres || ' ' || TEmpleado.apellidos AS nombre_completo, TPlantillaRol.descripcion AS departamento FROM rol.TEmpleado INNER JOIN rol.TPlantillaRol ON TEmpleado.codigo_plantilla = TPlantillaRol.codigo AND desafectado LIKE 'N'"

    token = request.headers.get('token')

    if departamento not in [None, '', 'N']:
        sql += f" WHERE TPlantillaRol.descripcion LIKE '{departamento}'"

    sql += " ORDER BY apellidos"

    return query_handler.execute_sql_token(sql, token, "")


@router.get("/obtener_grupos")
async def obtener_grupos(request: Request):
    sql = f"SELECT codigo, descripcion FROM rol.TPlantillaRol"
    token = request.headers.get('token')

    return query_handler.execute_sql_token(sql, token, "")


@router.get("/obtener_empleado_asignado")
async def obtener_emplado_asignado(request: Request):
    sql = "SELECT usuario_codigo FROM rol.tlugaresasignados"
    token = request.headers.get('token')
    return query_handler.execute_sql_token(sql, token, "")


@router.get("/obtener_empleados_asignados")
async def obtener_empleados_asignados(request: Request, departamento: str, lugar: str):
    sql = f"SELECT templeado.codigo, templeado.cedula_ruc, templeado.nombres || ' ' || templeado.apellidos AS nombre_completo, TPlantillaRol.descripcion AS departamento, talmacen.alm_nomcom, talmacen.alm_calles || ', ' || talmacen.alm_ciud AS direccion FROM rol.tlugaresasignados INNER JOIN rol.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN comun.talmacen ON talmacen.alm_codigo = tcoordenadas.alm_codigo INNER JOIN rol.templeado ON tlugaresasignados.usuario_codigo = templeado.codigo INNER JOIN rol.TPlantillaRol ON TEmpleado.codigo_plantilla = TPlantillaRol.codigo WHERE desafectado LIKE 'N'"
    token = request.headers.get('token')

    if departamento not in [None, '', 'N']:
        sql += f" AND TPlantillaRol.descripcion LIKE '{departamento}'"
    
    if lugar not in [None, '', 'N']:
        sql += f" AND talmacen.alm_nomcom LIKE '{lugar}'"

    sql += " ORDER BY nombre_completo"
    
    return query_handler.execute_sql_token(sql, token, "")


@router.get("/obtener_horarios_asignados")
async def obtener_horarios_asignados(request: Request, departamento: str, lugar: str, mes: str, anio: str):
    sql = f"SELECT thorariosasignados.codigo, thorariosasignados.usuario_codigo, templeado.nombres || ' ' || templeado.apellidos AS nombre_completo, TPlantillaRol.descripcion AS departamento, talmacen.alm_nomcom, thorariosasignados.horario_codigo, thorariosasignados.horario, thorariosasignados.nombre_horario, thorariosasignados.mes, thorariosasignados.anio FROM rol.thorariosasignados INNER JOIN rol.templeado ON thorariosasignados.usuario_codigo = templeado.codigo INNER JOIN rol.TPlantillaRol ON TEmpleado.codigo_plantilla = TPlantillaRol.codigo INNER JOIN comun.talmacen ON talmacen.alm_codigo = thorariosasignados.lugar_codigo WHERE desafectado LIKE 'N'"
    token = request.headers.get('token')

    nuevo_mes = utils.obtener_numero_mes(mes)

    if departamento not in [None, '', 'N']:
        sql += f" AND TPlantillaRol.descripcion LIKE '{departamento}'"

    if lugar not in [None, '', 'N']:
        sql += f" AND talmacen.alm_nomcom LIKE '{lugar}'"

    if mes not in [None, '', 'N', '0']:
        sql += f" AND thorariosasignados.mes = {nuevo_mes}"

    if anio not in [None, '', 'N', '0']:
        sql += f" AND thorariosasignados.anio = {int(anio)}"

    sql += " ORDER BY nombre_completo"

    return query_handler.execute_sql_token(sql, token, "")


@router.get("/obtener_empleados_horarios")
async def obtener_empleados_horarios(request: Request):
    sql = "SELECT usuario_codigo FROM rol.thorariosasignados WHERE horario_codigo IS NOT NULL"
    token = request.headers.get('token')
    return query_handler.execute_sql_token(sql, token, "")

@router.get("/obtener_empleados_horarios_actual")
async def obtener_empleados_horarios(request: Request):
    sql = """
    SELECT usuario_codigo 
    FROM rol.thorariosasignados 
    WHERE horario_codigo IS NOT NULL 
    AND EXTRACT(MONTH FROM CURRENT_DATE) = mes 
    AND EXTRACT(YEAR FROM CURRENT_DATE) = anio
    """
    token = request.headers.get('token')
    return query_handler.execute_sql_token(sql, token, "")

@router.get("/obtener_nombre_empleado")
async def obtener_nombre_empleado(request: Request, codigo: int):
    sql = f"SELECT nombres || ' ' || apellidos AS nombre_completo FROM rol.templeado WHERE codigo = {codigo}"
    token = request.headers.get('token')
    return query_handler.execute_sql_token(sql, token, "")

@router.delete("/eliminar_horario_asignado")
async def eliminar_horario_asignado(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    codigo = data['codigo']
    sql = f"DELETE FROM rol.thorariosasignados WHERE codigo = {codigo} RETURNING codigo"

    token = request.headers.get('token')
    usucodigo = request.headers.get('usucodigo')
    acceso = await acceso_middleware.tiene_acceso(usucodigo, 827, 1)

    if acceso[0]['tiene_acceso'] != '':
        return {
            "error": "S",
            "mensaje": acceso[0]['tiene_acceso'],
            "objetos": "",
        }

    return query_handler.execute_sql_token(sql, token, "Asignación de horario eliminada correctamente")
