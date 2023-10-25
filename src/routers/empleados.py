import json
import fastapi
from src import config
from src.utils import utils
from src.middleware import token_middleware
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


@router.get("/obtener_empleado")
async def obtener_empleado(request: Request, departamento: str):
    sql = f"SELECT TEmpleado.codigo, TEmpleado.cedula_ruc, TEmpleado.nombres || ' ' || TEmpleado.apellidos AS nombre_completo, TEmpleado.direccion, TEmpleado.cargo, TEmpleado.sueldo_basico, TEmpleado.fecha_ingreso, TEmpleado.no_telefono, TEmpleado.no_celular, TEmpleado.email, TPlantillaRol.descripcion AS departamento, CASE WHEN sexo = 'M' THEN 'Masculino' ELSE 'Femenino' END AS genero, CASE WHEN estado_civil = 'S' THEN 'Soltero(a)' WHEN estado_civil = 'C' THEN 'Casado(a)' WHEN estado_civil = 'D' THEN 'Divorciado(a)' WHEN estado_civil = 'V' THEN 'Viudo(s)' ELSE 'Unión Libre' END AS civil FROM rol.TEmpleado INNER JOIN rol.TPlantillaRol ON TEmpleado.codigo_plantilla = TPlantillaRol.codigo AND desafectado LIKE 'N'"

    token = request.headers.get('token')

    if departamento not in [None, '', 'N']:
        sql += f"WHERE TPlantillaRol.descripcion LIKE '{departamento}'"

    sql += " ORDER BY apellidos"
    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": "",
                    "objetos": rows,
                }

            empleados = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": empleados}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.get("/obtener_empleado_suplementarias")
async def obtener_empleado(request: Request, departamento: str):
    sql = f"SELECT TEmpleado.codigo, TEmpleado.nombres || ' ' || TEmpleado.apellidos AS nombre_completo, TPlantillaRol.descripcion AS departamento FROM rol.TEmpleado INNER JOIN rol.TPlantillaRol ON TEmpleado.codigo_plantilla = TPlantillaRol.codigo AND desafectado LIKE 'N'"

    token = request.headers.get('token')

    if departamento not in [None, '', 'N']:
        sql += f"WHERE TPlantillaRol.descripcion LIKE '{departamento}'"

    sql += " ORDER BY apellidos"
    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": "",
                    "objetos": rows,
                }

            empleados = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": empleados}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.get("/obtener_grupos")
async def obtener_grupos(request: Request):
    sql = f"SELECT codigo, descripcion FROM rol.TPlantillaRol"
    token = request.headers.get('token')

    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": "",
                    "objetos": rows,
                }

            grupos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": grupos}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.get("/obtener_empleado_asignado")
async def obtener_emplado_asignado(request: Request):
    sql = "SELECT usuario_codigo FROM comun.tlugaresasignados"
    token = request.headers.get('token')
    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": "",
                    "objetos": rows,
                }

            return {"error": "N", "mensaje": "", "objetos": rows}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.get("/obtener_empleados_asignados")
async def obtener_empleados_asignados(request: Request, lugar: str):
    sql = f"SELECT templeado.codigo, templeado.cedula_ruc, templeado.nombres || ' ' || templeado.apellidos AS nombre_completo, talmacen.alm_nomcom, talmacen.alm_calles || ', ' || talmacen.alm_ciud AS direccion FROM comun.tlugaresasignados INNER JOIN comun.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN comun.talmacen ON talmacen.alm_codigo = tcoordenadas.alm_codigo INNER JOIN rol.templeado ON tlugaresasignados.usuario_codigo = templeado.codigo"
    token = request.headers.get('token')

    if lugar not in [None, '', 'N']:
        sql += f" WHERE talmacen.alm_nomcom LIKE '{lugar}'"

    sql += " ORDER BY nombre_completo"

    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": "",
                    "objetos": rows,
                }

            asignaciones = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": asignaciones}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.get("/obtener_horarios_asignados")
async def obtener_empleados_asignados(request: Request, lugar: str):
    sql = f"SELECT tturnosasignados.codigo, templeado.nombres || ' ' || templeado.apellidos AS nombre_completo, talmacen.alm_nomcom, tturnos.dias_trabajados, talmacen.alm_calles || ', ' || talmacen.alm_ciud AS direccion, tturnos.inicio1 || ' ' || tturnos.fin1 AS Horario_1, tturnos.inicio2 || ' ' || tturnos.fin2 AS Horario_2 FROM comun.tlugaresasignados INNER JOIN comun.tcoordenadas ON tcoordenadas.codigo = tlugaresasignados.coordenadas_codigo INNER JOIN comun.talmacen ON talmacen.alm_codigo = tcoordenadas.alm_codigo INNER JOIN rol.templeado ON tlugaresasignados.usuario_codigo = templeado.codigo INNER JOIN comun.tturnosasignados ON tturnosasignados.usuario_codigo = tlugaresasignados.usuario_codigo INNER JOIN comun.tturnos ON tturnosasignados.turno_codigo = tturnos.codigo"
    token = request.headers.get('token')

    if lugar not in [None, '', 'N']:
        sql += f" WHERE talmacen.alm_nomcom LIKE '{lugar}'"

    sql += " ORDER BY nombre_completo"

    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": "",
                    "objetos": rows,
                }

            asignaciones = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": asignaciones}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.get("/obtener_empleados_horarios")
async def obtener_empleados_horarios(request: Request):
    sql = "SELECT usuario_codigo FROM comun.tturnosasignados WHERE turno_codigo IS NOT NULL"
    token = request.headers.get('token')
    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": "",
                    "objetos": rows,
                }

            return {"error": "N", "mensaje": "", "objetos": rows}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.delete("/eliminar_horario_asignado")
async def eliminar_horario_asignado(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    usuario_codigo = data['usuario_codigo']
    sql = f"DELETE FROM comun.tturnosasignados WHERE codigo = {usuario_codigo} RETURNING codigo"

    token = request.headers.get('token')

    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Asignación de horario eliminada correctamente", "objetos": objetos}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}
