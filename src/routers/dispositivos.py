import json
import fastapi
from src.config import config
from fastapi import Request
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text

# Establish connections to PostgreSQL databases for "apromed"
engine = create_engine(config.db_uri2)

# API Route Definitions
router = fastapi.APIRouter()


@router.post("/registrar_dispositivo")
async def registrar_dispositivo(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    usuario_codigo = data['usuario_codigo']
    id_dispositivo = data['id_dispositivo']

    verifica_sql = f"SELECT * FROM rol.tdispositivo WHERE usuario_codigo = '{usuario_codigo}' LIMIT 1"

    try:
        sql = f"INSERT INTO rol.tdispositivo (usuario_codigo, id_dispositivo) VALUES ('{usuario_codigo}', '{id_dispositivo.strip()}') RETURNING codigo"
        with Session(engine) as session:
            existe_registro = session.execute(text(verifica_sql)).fetchone()
            if existe_registro:
                return {"error": "S", "mensaje": 'Ya está registrado un dispositivo a su cuenta.', "objetos": []}
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Registro de dispositivo exitoso", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.get("/validar_dispositivo")
async def validar_dispositivo(id: str):
    sql = f"SELECT * FROM rol.tdispositivo WHERE TRIM(id_dispositivo) LIKE '{id.strip()}'"
    try:
        with Session(engine) as session:
            rows = session.execute(text(sql)).fetchall()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": f"No se encuentra un dispositivo registrado con el id {id} en el sistema ",
                    "objetos": rows,
                }

            dispositivo = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": dispositivo[0]}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}
