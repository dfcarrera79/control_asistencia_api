import json
import fastapi
from src import config
from fastapi import Request
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text

# Establish connections to PostgreSQL databases for "reclamos" and "apromed" respectively
db_uri1 = config.db_uri1
engine1 = create_engine(db_uri1)

db_uri2 = config.db_uri2
engine2 = create_engine(db_uri2)

# API Route Definitions
router = fastapi.APIRouter()


@router.post("/registrar_dispositivo")
async def registrar_dispositivo(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    ruc = data['ruc']
    id_dispositivo = data['id_dispositivo']
    try:
        sql = f"INSERT INTO dispositivo (ruc_cliente, id_dispositivo) VALUES ('{ruc.strip()}', '{id_dispositivo.strip()}') RETURNING id"
        print('[SQL]: ', sql)
        with Session(engine1) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Registro de dispositivo exitoso", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.get("/validar_dispositivo")
async def validar_dispositivo(id: str):
    sql = f"SELECT * FROM dispositivo WHERE TRIM(id_dispositivo) LIKE '{id.strip()}'"
    print('[SQL]: ', sql)
    try:
        with Session(engine1) as session:
            rows = session.execute(text(sql)).fetchall()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": f"No se encuentra un dispositivo registrado con el id {id} en el sistema ",
                    "objetos": rows,
                }

            dispositivo = [row._asdict() for row in rows]
            print('[DISPOSITIVO]: ', dispositivo)
            return {"error": "N", "mensaje": "", "objetos": dispositivo[0]}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}
