import json
import fastapi
from src import config
from fastapi import Request
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from src.middleware import token_middleware, acceso_middleware
from sqlalchemy import text, create_engine


# Establish connections to PostgreSQL databases for "reclamos" and "apromed" respectively
db_uri1 = config.db_uri1
engine1 = create_engine(db_uri1)

db_uri2 = config.db_uri2
engine2 = create_engine(db_uri2)

# API Route Definitions
router = fastapi.APIRouter()


@router.get("/tiene_acceso")
async def tiene_acceso(usucodigo: int, modcodigo: int, accion: int):
    sql = f"SELECT * FROM usuario.tiene_acceso({usucodigo}, {modcodigo}, {accion})"
    try:
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            acceso = [row._asdict() for row in rows]
            if acceso[0]['tiene_acceso'] != '':
                return {
                    "error": "S",
                    "mensaje": acceso[0]['tiene_acceso'],
                    "objetos": "",
                }
            return {"error": "N", "mensaje": acceso[0]['tiene_acceso'], "objetos": ""}
    except Exception as e:
        print(f"Error: {e}")
        return {"error": "S", "mensaje": str(e)}


@router.get("/obtener_dispositivos")
async def obtener_dispositivos(request: Request, departamento: str):
    sql = f"SELECT tdispositivo.codigo, TEmpleado.cedula_ruc, TEmpleado.nombres || ' ' || TEmpleado.apellidos AS nombre_completo, TPlantillaRol.descripcion AS departamento, tdispositivo.id_dispositivo FROM rol.TEmpleado INNER JOIN rol.TPlantillaRol ON TEmpleado.codigo_plantilla = TPlantillaRol.codigo INNER JOIN comun.tdispositivo ON TEmpleado.codigo = tdispositivo.usuario_codigo WHERE TEmpleado.desafectado = 'N'"
    token = request.headers.get('token')

    if departamento not in [None, '', 'N']:
        sql += f" AND TPlantillaRol.descripcion LIKE '{departamento}'"

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

            dispositivos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": dispositivos}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.get("/obtener_fotos")
async def obtener_fotos(request: Request, departamento: str):
    sql = f"SELECT tfoto.id_foto, TEmpleado.cedula_ruc, TEmpleado.nombres || ' ' || TEmpleado.apellidos AS nombre_completo, TPlantillaRol.descripcion AS departamento, tfoto.path FROM rol.TEmpleado INNER JOIN rol.TPlantillaRol ON TEmpleado.codigo_plantilla = TPlantillaRol.codigo INNER JOIN comun.tfoto ON TEmpleado.codigo = tfoto.usuario_codigo WHERE TEmpleado.desafectado = 'N'"
    token = request.headers.get('token')

    if departamento not in [None, '', 'N']:
        sql += f" AND TPlantillaRol.descripcion LIKE '{departamento}'"

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

            fotos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": fotos}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


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

    sql = f"DELETE FROM comun.tfoto WHERE id_foto = {id_foto} RETURNING path, usuario_codigo"
    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Registro eliminado exitosamente", "objetos": objetos}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


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

    sql = f"DELETE FROM comun.tdispositivo WHERE codigo = {codigo} RETURNING id_dispositivo, usuario_codigo"
    print('[SQL]: ', sql)
    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Registro eliminado exitosamente", "objetos": objetos}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.post("/copiar_path_id")
async def copiar_path_id(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    usuario_codigo = data['usuario_codigo']
    pathorid = data['pathorid']
    anulado_por = data['anulado_por']
    token = request.headers.get('token')
    sql = f"INSERT INTO comun.trespaldofotocel (usuario_codigo, pathorid, anulado_por) VALUES({usuario_codigo}, '{pathorid}', {anulado_por}) RETURNING id_registro"
    try:
        token_middleware.verify_token(token)
        with Session(engine2) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Registro anulado exitosamente", "objetos": objetos}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.get("/obtener_anulados")
async def obtener_anulados(request: Request, departamento: str):
    sql = "SELECT id_registro AS codigo, TEmpleado.nombres || ' ' || TEmpleado.apellidos AS nombre_completo, TPlantillaRol.descripcion AS departamento, pathorid AS registro, TUsuario.usu_nomape AS anulado_por FROM comun.trespaldofotocel INNER JOIN rol.TEmpleado ON trespaldofotocel.usuario_codigo = TEmpleado.codigo INNER JOIN usuario.TUsuario ON trespaldofotocel.anulado_por = TUsuario.usu_codigo INNER JOIN rol.TPlantillaRol ON TEmpleado.codigo_plantilla = TPlantillaRol.codigo"
    token = request.headers.get('token')

    if departamento not in [None, '', 'N']:
        sql += f" AND TPlantillaRol.descripcion LIKE '{departamento}'"

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

            registros = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": registros}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}
