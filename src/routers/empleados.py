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


@router.get("/obtener_empleado")
async def obtener_empleado(request: Request, departamento: str):
    sql = f"SELECT TEmpleado.codigo, TEmpleado.cedula_ruc, TEmpleado.nombres || ' ' || TEmpleado.apellidos AS nombre_completo, TEmpleado.direccion, TEmpleado.cargo, TEmpleado.sueldo_basico, TEmpleado.fecha_ingreso, TEmpleado.no_telefono, TEmpleado.no_celular, TEmpleado.email, TPlantillaRol.descripcion AS departamento, CASE WHEN sexo = 'M' THEN 'Masculino' ELSE 'Femenino' END AS genero, CASE WHEN estado_civil = 'S' THEN 'Soltero(a)' WHEN estado_civil = 'C' THEN 'Casado(a)' WHEN estado_civil = 'D' THEN 'Divorciado(a)' WHEN estado_civil = 'V' THEN 'Viudo(s)' ELSE 'Unión Libre' END AS civil FROM rol.TEmpleado INNER JOIN rol.TPlantillaRol ON TEmpleado.codigo_plantilla = TPlantillaRol.codigo AND desafectado LIKE 'N'"

    token = request.headers.get('token')

    if departamento not in [None, '', 'N']:
        sql += f"WHERE TPlantillaRol.descripcion LIKE '{departamento}'"

    sql += " ORDER BY apellidos"
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

            empleados = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": empleados}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.get("/obtener_grupos")
async def obtener_grupos(request: Request):
    sql = f"SELECT codigo, descripcion FROM rol.TPlantillaRol"
    token = request.headers.get('token')

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

            grupos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": grupos}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}
