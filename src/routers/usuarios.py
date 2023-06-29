import json
import fastapi
from src import config
from src.utils import utils
from fastapi import Request
from sqlalchemy.orm import Session
from email.message import EmailMessage
from sqlalchemy import create_engine, text
from src.utils.utils import generate_random_string


# Establish connections to PostgreSQL databases for "reclamos" and "apromed" respectively
db_uri1 = config.db_uri1
engine1 = create_engine(db_uri1)

db_uri2 = config.db_uri2
engine2 = create_engine(db_uri2)


# API Route Definitions
router = fastapi.APIRouter()


@router.get("/validar_usuario")
async def validar_cliente(id: str, clave: str):
    sql = f"SELECT * FROM usuario WHERE TRIM(ruc_cliente) LIKE '{id.strip()}'"
    try:
        with Session(engine1) as session:
            rows = session.execute(text(sql)).fetchall()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": f"No se encuentra un usuario registrado con el RUC Nro. {id} en el sistema de reclamos",
                    "objetos": rows,
                }

            clienteApp = [row._asdict() for row in rows]

            if clienteApp[0]["clave"] == utils.codify(clave):
                # Generate authentication token
                token = utils.generate_token(id, clave)
                return {"error": "N", "mensaje": "", "objetos": clienteApp, 'token': token}
            else:
                return {
                    "error": "S",
                    "mensaje": f"La clave de acceso ingresada no es correcta, no puede acceder al sistema",
                    "objetos": rows,
                }
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.get("/obtener_usuario")
async def obtener_usuario(id: str):
    sql = f"SELECT * FROM usuario WHERE TRIM(ruc_cliente) LIKE '{id.strip()}'"
    try:
        with Session(engine1) as session:
            rows = session.execute(text(sql)).fetchall()
            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": f"No se encuentra un usuario registrado con el RUC Nro. {id} en el sistema de reclamos",
                    "objetos": rows,
                }

            usuario = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": usuario[0]['email']}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.put("/resetear_clave_acceso")
async def resetear_clave_acceso(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    ruc = data['ruc']
    email = data['email']
    clave = generate_random_string(10)
    subject = 'Nueva clave de acceso'
    message = f"""Estimad@, mediante el presente email le enviamos la nueva clave generada y le recomendamos cambiarla lo antes posible por una personal.
            
    <p><strong>Nueva clave: </strong>{clave}</p>
    
    <p><a href='http://localhost:9000/#/cambiar_clave/{ruc}'>Cambiar la clave de acceso</a></p>"""

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = '"LoxaSoluciones" <soporte@loxasoluciones.com>'
    msg['To'] = email
    msg.set_content(message, subtype='html')
    try:
        response = await utils.email_alert(msg)
        nueva_clave = utils.codify(clave)
        sql = f"UPDATE usuario SET clave = '{nueva_clave}' WHERE ruc_cliente = '{ruc.strip()}' RETURNING ruc_cliente"
        if response['ok']:
            with Session(engine1) as session:
                rows = session.execute(text(sql)).fetchall()
                session.commit()
                objetos = [row._asdict() for row in rows]
                return {"error": "N", "mensaje": "", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.put("/cambiar_clave")
async def resetear_clave_acceso(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    ruc = data['ruc']
    clave = data['clave']
    print('[RUC]: ', ruc)
    print('[CLAVE]: ', clave)
    try:
        nueva_clave = utils.codify(clave)
        sql = f"UPDATE usuario SET clave = '{nueva_clave}' WHERE ruc_cliente = '{ruc.strip()}' RETURNING ruc_cliente"
        print('[SQL]: ', sql)
        with Session(engine1) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}
