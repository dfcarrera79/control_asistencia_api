import json
import fastapi
from src import config
from src.utils import utils
from src.middleware import token_middleware
from datetime import datetime
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text

# Establish connections to PostgreSQL databases for "reclamos" and "apromed" respectively
db_uri1 = config.db_uri1
engine1 = create_engine(db_uri1)

db_uri2 = config.db_uri2
engine2 = create_engine(db_uri2)

# API Route Definitions
router = fastapi.APIRouter()


async def registrar_detalle_cierre(codigo: int, normal: float, suplementaria: float, atrasos: float, usuario_codigo: int):
    # Reemplaza los valores None con 0 para la consulta SQL
    codigo = codigo if codigo is not None else 0
    normal = normal if normal is not None else 0
    suplementaria = suplementaria if suplementaria is not None else 0
    atrasos = atrasos if atrasos is not None else 0
    usuario_codigo = usuario_codigo if usuario_codigo is not None else 0

    sql = f"INSERT INTO comun.tdetallemes (codigo_cierre, normal, suplementaria, atrasos, usuario_codigo) VALUES ('{codigo}', '{normal}', '{suplementaria}', '{atrasos}', '{usuario_codigo}') RETURNING codigo_detalle"

    with Session(engine2) as session:
        try:
            # Ejecutar la consulta SQL
            rows = session.execute(text(sql)).fetchall()
            # Confirmar la transacción
            session.commit()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": "",
                    "objetos": rows,
                }
        except Exception as error:
            # En caso de error, realizar un rollback para deshacer cambios
            session.rollback()
            return {
                "error": "S",
                "mensaje": str(error),
            }


@router.post("/registrar_consolidacion")
async def registrar_consolidacion(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    mes = data['mes']
    anio = data['anio']
    usuario_creo = data['usuarioCreo']
    datos = data['datos']

    token = request.headers.get('token')

    # Consulta para verificar si ya existe un registro con el mismo año y mes
    verifica_sql = f"SELECT codigo_cierre FROM comun.tcierremes WHERE mes = '{mes}' AND anio = '{anio}' AND anulado = 'N' LIMIT 1"

    sql = f"INSERT INTO comun.tcierremes (mes, anio, usuario_creo, fecha_creacion, anulado) VALUES ('{mes}', '{anio}', '{usuario_creo}', NOW(), 'N') RETURNING codigo_cierre"

    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            # Verificar si ya existe un registro
            existing_cierre = session.execute(text(verifica_sql)).fetchone()
            if existing_cierre:
                return {"error": "S", "mensaje": 'Ya existe un cierre con el mes y año seleccionado', "objetos": []}
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]

            for dato in datos:
                codigo_cierre = objetos[0]['codigo_cierre']
                normal = dato['horas_trabajadas']
                suplementaria = dato['horas_suplementarias']
                atrasos = dato['atrasos']
                codigo_usuario = dato['codigo']
                await registrar_detalle_cierre(codigo_cierre, normal, suplementaria, atrasos, codigo_usuario)

            return {"error": "N", "mensaje": "Registro de consolidacién de mes exitoso", "objetos": objetos}

    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.get("/listar_consolidaciones")
async def listar_consolidaciones(request: Request, mes: int, anio: int):
    token = request.headers.get('token')
    verifica_sql = f"SELECT codigo_cierre FROM comun.tcierremes WHERE mes = '{mes}' AND anio = '{anio}' AND anulado = 'N' "

    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            codigo = session.execute(text(verifica_sql)).fetchone()

            if (codigo == None):
                return {"error": "S", "mensaje": 'No existen registros con esa fecha', "objetos": []}

            sql = f"SELECT codigo_detalle, templeado.nombres || ' ' || templeado.apellidos AS nombre_completo, TPlantillaRol.descripcion AS departamento, normal, suplementaria, atrasos FROM comun.tdetallemes INNER JOIN rol.templeado ON tdetallemes.usuario_codigo = templeado.codigo INNER JOIN rol.TPlantillaRol ON TEmpleado.codigo_plantilla = TPlantillaRol.codigo WHERE codigo_cierre = {codigo[0]}"

            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]

            return {"error": "N", "mensaje": codigo[0], "objetos": objetos}

    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.put("/anular_consolidacion")
async def anular_consolidacion(request: Request):
    token = request.headers.get('token')
    request_body = await request.body()
    data = json.loads(request_body)
    codigo_cierre = data['codigoCierre']
    usuario_actualizo = data['usuarioActualizo']
    sql = f"UPDATE comun.tcierremes SET anulado = 'S', usuario_actualizo = '{usuario_actualizo}', fecha_actualizo = NOW()  WHERE codigo_cierre = {codigo_cierre} RETURNING codigo_cierre"

    print('[SQL]: ', sql)

    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]

            return {"error": "N", "mensaje": "Registro anulado exitosamente", "objetos": objetos}

    except Exception as error:
        return {"error": "S", "mensaje": str(error)}
